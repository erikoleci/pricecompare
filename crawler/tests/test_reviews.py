"""
Integration test for reviews (spec sections 16-17): write_reviews() only
ever persists reviews a connector actually returned, review_summary is a
pure aggregate of what's in `reviews` (never fabricated), and re-writing
the same scraped reviews (e.g. a re-crawl) doesn't duplicate rows.
"""

from __future__ import annotations

import os
from decimal import Decimal

import psycopg
import pytest
from psycopg.rows import dict_row

from crawler.interfaces.merchant_connector import RawReview
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


@pytest.fixture
def db_setup():
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        conn.execute("DELETE FROM merchants WHERE domain = 'reviews-test.example'")
        merchant_row = conn.execute(
            "INSERT INTO merchants (name, domain, currency, status, crawler_enabled) "
            "VALUES ('Reviews Test Merchant', 'reviews-test.example', 'EUR', 'ACTIVE', true) RETURNING id"
        ).fetchone()
        merchant_id = str(merchant_row["id"])

        product_row = conn.execute(
            "INSERT INTO products (title, normalized_title) VALUES ('Test Product For Reviews', 'test product for reviews') RETURNING id"
        ).fetchone()
        product_id = str(product_row["id"])
        conn.commit()

        yield conn, merchant_id, product_id

        conn.execute("DELETE FROM products WHERE id = %s", (product_id,))
        conn.execute("DELETE FROM merchants WHERE id = %s", (merchant_id,))
        conn.commit()


def test_write_reviews_and_summary(db_setup):
    conn, merchant_id, product_id = db_setup
    storage = OfferStorage(StorageConfig(dsn=DSN))

    reviews = [
        RawReview(author_name="Ana", rating=5.0, title="Great!", text="Loved it", review_date="2026-01-05", verified=True),
        RawReview(author_name="Beni", rating=4.0, title=None, text="Good value", review_date="2026-02-10", verified=False),
        RawReview(author_name="Cel", rating=3.0, title=None, text=None, review_date=None, verified=False),
    ]

    inserted = storage.write_reviews(conn, product_id=product_id, merchant_id=merchant_id,
                                      source="reviews-test.example", reviews=reviews)
    conn.commit()
    assert inserted == 3

    rows = conn.execute("SELECT rating, verified FROM reviews WHERE product_id = %s ORDER BY rating DESC",
                         (product_id,)).fetchall()
    assert len(rows) == 3
    assert [float(r["rating"]) for r in rows] == [5.0, 4.0, 3.0]
    assert rows[0]["verified"] is True

    summary = conn.execute("SELECT average_rating, review_count, rating_distribution FROM review_summary WHERE product_id = %s",
                            (product_id,)).fetchone()
    assert summary is not None
    assert float(summary["average_rating"]) == pytest.approx(4.0, abs=0.01)
    assert summary["review_count"] == 3
    assert summary["rating_distribution"]["5"] == 1
    assert summary["rating_distribution"]["4"] == 1
    assert summary["rating_distribution"]["3"] == 1


def test_write_reviews_does_not_duplicate_on_recrawl(db_setup):
    conn, merchant_id, product_id = db_setup
    storage = OfferStorage(StorageConfig(dsn=DSN))

    review = [RawReview(author_name="Dea", rating=5.0, title="X", text="Y", review_date="2026-03-01", verified=True)]

    first = storage.write_reviews(conn, product_id=product_id, merchant_id=merchant_id,
                                   source="reviews-test.example", reviews=review)
    conn.commit()
    assert first == 1

    # Simulate a re-crawl of the exact same review page - must not duplicate.
    second = storage.write_reviews(conn, product_id=product_id, merchant_id=merchant_id,
                                    source="reviews-test.example", reviews=review)
    conn.commit()
    assert second == 0

    count = conn.execute("SELECT count(*) AS c FROM reviews WHERE product_id = %s", (product_id,)).fetchone()
    assert count["c"] == 1


def test_no_reviews_means_no_summary_row(db_setup):
    """If a connector never returns reviews (the default for extract_reviews()),
    nothing is fabricated - no review_summary row is created at all."""
    conn, merchant_id, product_id = db_setup
    summary = conn.execute("SELECT * FROM review_summary WHERE product_id = %s", (product_id,)).fetchone()
    assert summary is None
