"""
Phase 3: end-to-end test of OfferStorage.process_raw_offer(), which wires the
section-15 matcher (crawler/normalizers/product_matcher.py) into the DB
pipeline. Requires a running Postgres with the schema applied - skips
cleanly if unreachable, same as test_pipeline_integration.py.

Covers the three outcomes the spec requires:
  1. Same EAN from two merchants -> same product (AUTO_MERGED)
  2. Different brand/model -> a separate product (NEW_PRODUCT)
  3. Same brand+model, similar-but-not-identical specs -> a *separate*
     product, but flagged in product_match_candidates for manual review
     (confidence in the 70-89 "possible match" band is never auto-merged)
"""

from __future__ import annotations

import os
import uuid
from decimal import Decimal

import psycopg
import pytest
from psycopg.rows import dict_row

from crawler.interfaces.merchant_connector import RawOffer, RawSpecification
from crawler.storage.offer_storage import OfferStorage, StorageConfig

DSN = os.environ.get(
    "PRICECOMPARE_TEST_DSN",
    "host=localhost dbname=pricecompare user=pricecompare password=pricecompare_dev_password",
)


def _db_available() -> bool:
    try:
        with psycopg.connect(DSN, connect_timeout=2):
            return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="Postgres not reachable in this environment")


def _make_merchant(conn, domain: str) -> str:
    conn.execute("DELETE FROM merchants WHERE domain = %s", (domain,))
    row = conn.execute(
        "INSERT INTO merchants (name, domain, currency, status, crawler_enabled) "
        "VALUES (%s, %s, 'EUR', 'ACTIVE', true) RETURNING id",
        (domain, domain),
    ).fetchone()
    return str(row["id"])


def _make_brand(conn, name: str) -> str:
    row = conn.execute("SELECT id FROM brands WHERE lower(name) = lower(%s)", (name,)).fetchone()
    if row:
        return str(row["id"])
    row = conn.execute(
        "INSERT INTO brands (name, slug) VALUES (%s, %s) RETURNING id",
        (name, name.lower().replace(" ", "-") + "-" + uuid.uuid4().hex[:6]),
    ).fetchone()
    return str(row["id"])


def _make_category(conn, name: str) -> str:
    row = conn.execute("SELECT id FROM categories WHERE lower(name) = lower(%s)", (name,)).fetchone()
    if row:
        return str(row["id"])
    row = conn.execute(
        "INSERT INTO categories (name, slug) VALUES (%s, %s) RETURNING id",
        (name, name.lower().replace(" ", "-") + "-" + uuid.uuid4().hex[:6]),
    ).fetchone()
    return str(row["id"])


@pytest.fixture()
def conn():
    with psycopg.connect(DSN, row_factory=dict_row) as connection:
        yield connection
        connection.rollback()


def test_same_ean_from_two_merchants_links_to_one_product(conn):
    storage = OfferStorage(StorageConfig(dsn=DSN))
    brand_id = _make_brand(conn, "TestBrand-EAN")
    category_id = _make_category(conn, "TestCategory-EAN")
    ean = "0" + uuid.uuid4().hex[:12]

    merchant_a = _make_merchant(conn, "merchant-a-ean.example")
    merchant_b = _make_merchant(conn, "merchant-b-ean.example")

    offer_a = RawOffer(
        merchant_domain="merchant-a-ean.example", merchant_product_id="A-1",
        title="Apple iPhone 17 Pro 256GB Black", url="https://merchant-a-ean.example/p/1",
        price=Decimal("899.00"), currency="EUR", brand="TestBrand-EAN", model="iPhone 17 Pro",
        ean=ean, source_url="https://merchant-a-ean.example/p/1",
    )
    offer_b = RawOffer(
        merchant_domain="merchant-b-ean.example", merchant_product_id="B-1",
        title="iPhone 17 Pro 256 GB Black", url="https://merchant-b-ean.example/p/1",
        price=Decimal("879.00"), currency="EUR", brand="TestBrand-EAN", model="iPhone 17 Pro",
        ean=ean, source_url="https://merchant-b-ean.example/p/1",
    )

    result_a = storage.process_raw_offer(conn, merchant_id=merchant_a, raw=offer_a,
                                          category_id=category_id, brand_id=brand_id)
    assert result_a["match_decision"] == "NEW_PRODUCT"  # nothing to match against yet

    result_b = storage.process_raw_offer(conn, merchant_id=merchant_b, raw=offer_b,
                                          category_id=category_id, brand_id=brand_id)
    assert result_b["match_decision"] == "AUTO_MERGED"
    assert result_b["match_confidence"] == 100.0
    assert result_b["product_id"] == result_a["product_id"]  # same product, two offers


def test_different_brand_model_creates_separate_products(conn):
    storage = OfferStorage(StorageConfig(dsn=DSN))
    brand_id = _make_brand(conn, "TestBrand-DIFF")
    category_id = _make_category(conn, "TestCategory-DIFF")
    merchant_id = _make_merchant(conn, "merchant-diff.example")

    offer_1 = RawOffer(
        merchant_domain="merchant-diff.example", merchant_product_id="D-1",
        title="Samsung Galaxy S26 Ultra 512GB", url="https://merchant-diff.example/p/1",
        price=Decimal("1199.00"), currency="EUR", brand="TestBrand-DIFF", model="Galaxy S26 Ultra",
        source_url="https://merchant-diff.example/p/1",
    )
    offer_2 = RawOffer(
        merchant_domain="merchant-diff.example", merchant_product_id="D-2",
        title="Samsung Galaxy Watch 7", url="https://merchant-diff.example/p/2",
        price=Decimal("299.00"), currency="EUR", brand="TestBrand-DIFF", model="Galaxy Watch 7",
        source_url="https://merchant-diff.example/p/2",
    )

    result_1 = storage.process_raw_offer(conn, merchant_id=merchant_id, raw=offer_1,
                                          category_id=category_id, brand_id=brand_id)
    result_2 = storage.process_raw_offer(conn, merchant_id=merchant_id, raw=offer_2,
                                          category_id=category_id, brand_id=brand_id)

    assert result_1["product_id"] != result_2["product_id"]
    assert result_2["match_decision"] == "NEW_PRODUCT"


def test_same_brand_model_conflicting_specs_flagged_for_review_not_auto_merged(conn):
    storage = OfferStorage(StorageConfig(dsn=DSN))
    brand_id = _make_brand(conn, "TestBrand-REVIEW")
    category_id = _make_category(conn, "TestCategory-REVIEW")
    merchant_id = _make_merchant(conn, "merchant-review.example")

    offer_1 = RawOffer(
        merchant_domain="merchant-review.example", merchant_product_id="R-1",
        title="TestBrand-REVIEW Widget X1", url="https://merchant-review.example/p/1",
        price=Decimal("499.00"), currency="EUR", brand="TestBrand-REVIEW", model="Widget X1",
        specifications=[RawSpecification(key="storage", value="128GB"),
                         RawSpecification(key="color", value="Black")],
        source_url="https://merchant-review.example/p/1",
    )
    # same brand+model, but every comparable spec disagrees -> brand+model score
    # lands in the 70-89 "possible match" band, per score_brand_model_match
    offer_2 = RawOffer(
        merchant_domain="merchant-review.example", merchant_product_id="R-2",
        title="TestBrand-REVIEW Widget X1", url="https://merchant-review.example/p/2",
        price=Decimal("479.00"), currency="EUR", brand="TestBrand-REVIEW", model="Widget X1",
        specifications=[RawSpecification(key="storage", value="256GB"),
                         RawSpecification(key="color", value="Silver")],
        source_url="https://merchant-review.example/p/2",
    )

    storage.process_raw_offer(conn, merchant_id=merchant_id, raw=offer_1,
                               category_id=category_id, brand_id=brand_id)
    result_2 = storage.process_raw_offer(conn, merchant_id=merchant_id, raw=offer_2,
                                          category_id=category_id, brand_id=brand_id)

    assert result_2["match_decision"] == "NEW_PRODUCT_PENDING_REVIEW"
    assert 70.0 <= result_2["match_confidence"] < 90.0

    candidate_row = conn.execute(
        "SELECT status, match_method FROM product_match_candidates WHERE offer_id = %s",
        (result_2["offer_id"],),
    ).fetchone()
    assert candidate_row is not None
    assert candidate_row["status"] == "PENDING"
    assert candidate_row["match_method"] == "BRAND_MODEL"
