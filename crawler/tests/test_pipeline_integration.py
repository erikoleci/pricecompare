"""
End-to-end test: parses the fixture HTML, normalizes it, and writes it
through the real storage layer into Postgres, then asserts what landed in
the DB. Requires a running Postgres with the schema applied (see README) -
skips cleanly if the DB isn't reachable so the rest of the suite still runs
in environments without Postgres.
"""

from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path

import psycopg
import pytest

from crawler.core.compliance import MerchantPolicy, ComplianceGate
from crawler.merchants.demo_electronics_store.connector import DemoElectronicsStoreConnector
from crawler.normalizers.product_normalizer import normalize_title, build_identifier_candidates
from crawler.storage.offer_storage import OfferStorage, StorageConfig

FIXTURE = Path(__file__).parent / "fixtures" / "demo_store_product.html"
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


def test_full_pipeline_fixture_to_database():
    policy = MerchantPolicy(domain="demo-electronics.example", base_url="https://demo-electronics.example",
                             is_supported=True)
    connector = DemoElectronicsStoreConnector(policy, ComplianceGate())

    html = FIXTURE.read_text()
    raw = connector.parse_offer(html, url="https://demo-electronics.example/p/ip17p-256-black")

    # --- assert extraction is correct before it ever touches the DB ---
    assert raw.price == Decimal("899.00")
    assert raw.old_price == Decimal("999.00")
    assert raw.shipping_cost == Decimal("4.99")
    assert raw.availability == "IN_STOCK"
    assert raw.ean == "0194253001234"
    assert len(raw.specifications) == 4
    assert len(raw.images) == 2

    normalized = normalize_title(raw.title)
    identifiers = build_identifier_candidates(raw)
    assert identifiers[0] == ("EAN", raw.ean)

    from psycopg.rows import dict_row

    storage = OfferStorage(StorageConfig(dsn=DSN))
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        conn.execute("DELETE FROM offers WHERE merchant_product_id = %s", (raw.merchant_product_id,))
        conn.execute("DELETE FROM merchants WHERE domain = %s", (raw.merchant_domain,))
        merchant_row = conn.execute(
            "INSERT INTO merchants (name, domain, currency, status, crawler_enabled) "
            "VALUES ('Demo Electronics Store', %s, 'EUR', 'ACTIVE', true) RETURNING id",
            (raw.merchant_domain,),
        ).fetchone()
        merchant_id = str(merchant_row["id"])

        product_id = storage.upsert_product(
            conn, product_id=None, title=raw.title, normalized_title=normalized,
            brand_id=None, category_id=None, model="iPhone 17 Pro", description=raw.description,
        )

        result = storage.upsert_offer_and_record_price(
            conn,
            product_id=product_id,
            merchant_id=merchant_id,
            merchant_product_id=raw.merchant_product_id,
            price=raw.price,
            currency=raw.currency,
            old_price=raw.old_price,
            shipping_cost=raw.shipping_cost,
            availability=raw.availability,
            condition=raw.condition,
            url=raw.url,
            image_url=raw.images[0].url if raw.images else None,
            source_url=raw.source_url,
        )

        # --- assert what actually landed in the DB ---
        offer_row = conn.execute(
            "SELECT price, shipping_cost, total_price, availability FROM offers WHERE id = %s",
            (result["offer_id"],),
        ).fetchone()
        assert offer_row["price"] == Decimal("899.00")
        assert offer_row["shipping_cost"] == Decimal("4.99")
        assert offer_row["total_price"] == Decimal("903.99")  # price + shipping
        assert offer_row["availability"] == "IN_STOCK"

        history_count = conn.execute(
            "SELECT count(*) as c FROM price_history WHERE offer_id = %s", (result["offer_id"],)
        ).fetchone()["c"]
        assert history_count == 1

        # simulate a second crawl with a price drop and confirm a price_drop_event is recorded
        result2 = storage.upsert_offer_and_record_price(
            conn,
            product_id=product_id,
            merchant_id=merchant_id,
            merchant_product_id=raw.merchant_product_id,
            price=Decimal("799.00"),
            currency=raw.currency,
            old_price=raw.price,
            shipping_cost=raw.shipping_cost,
            availability=raw.availability,
            condition=raw.condition,
            url=raw.url,
            image_url=None,
            source_url=raw.source_url,
        )
        drop_count = conn.execute(
            "SELECT count(*) as c FROM price_drop_events WHERE offer_id = %s", (result2["offer_id"],)
        ).fetchone()["c"]
        assert drop_count == 1

        history_count_after = conn.execute(
            "SELECT count(*) as c FROM price_history WHERE offer_id = %s", (result2["offer_id"],)
        ).fetchone()["c"]
        assert history_count_after == 2  # append-only, never overwritten

        # cleanup
        conn.execute("DELETE FROM merchants WHERE id = %s", (merchant_id,))
        conn.commit()
