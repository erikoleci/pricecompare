"""
Phase 4: price alerts (spec section 22). Verifies OfferStorage fires an
alert the moment the best available price for a product drops to or below
the user's target, marks it triggered exactly once, and leaves alerts
above target untouched.
"""

from __future__ import annotations

import os
import uuid
from decimal import Decimal

import psycopg
import pytest
from psycopg.rows import dict_row

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


@pytest.fixture()
def conn():
    with psycopg.connect(DSN, row_factory=dict_row) as connection:
        yield connection
        connection.rollback()


def _make_user(conn) -> str:
    row = conn.execute(
        "INSERT INTO users (email, password_hash, display_name) VALUES (%s, 'x', 'Test User') RETURNING id",
        (f"alert-test-{uuid.uuid4().hex[:8]}@example.com",),
    ).fetchone()
    return str(row["id"])


def _make_product(conn) -> str:
    row = conn.execute(
        "INSERT INTO products (title, normalized_title) VALUES ('Alert Test Product', 'alert test product') "
        "RETURNING id"
    ).fetchone()
    return str(row["id"])


def _make_merchant(conn, domain: str) -> str:
    row = conn.execute(
        "INSERT INTO merchants (name, domain, currency, status, crawler_enabled) "
        "VALUES (%s, %s, 'EUR', 'ACTIVE', true) RETURNING id",
        (domain, domain),
    ).fetchone()
    return str(row["id"])


def test_alert_fires_when_price_drops_to_target(conn):
    storage = OfferStorage(StorageConfig(dsn=DSN))
    product_id = _make_product(conn)
    merchant_id = _make_merchant(conn, f"alert-merchant-{uuid.uuid4().hex[:8]}.example")
    user_id = _make_user(conn)

    alert = conn.execute(
        "INSERT INTO price_alerts (user_id, product_id, target_price) VALUES (%s, %s, %s) RETURNING id",
        (user_id, product_id, Decimal("850.00")),
    ).fetchone()

    # first price (899) is above target - alert must not fire yet
    result_1 = storage.upsert_offer_and_record_price(
        conn, product_id=product_id, merchant_id=merchant_id, merchant_product_id="M-1",
        price=Decimal("899.00"), currency="EUR", old_price=None, shipping_cost=None,
        availability="IN_STOCK", condition="NEW", url="https://x.example/1", image_url=None,
        source_url="https://x.example/1",
    )
    assert result_1["fired_alerts"] == []

    # price drops to 829, below the 850 target - alert should fire exactly once
    result_2 = storage.upsert_offer_and_record_price(
        conn, product_id=product_id, merchant_id=merchant_id, merchant_product_id="M-1",
        price=Decimal("829.00"), currency="EUR", old_price=Decimal("899.00"), shipping_cost=None,
        availability="IN_STOCK", condition="NEW", url="https://x.example/1", image_url=None,
        source_url="https://x.example/1",
    )
    assert len(result_2["fired_alerts"]) == 1
    assert result_2["fired_alerts"][0]["alert_id"] == str(alert["id"])

    row = conn.execute(
        "SELECT active, triggered_at FROM price_alerts WHERE id = %s", (alert["id"],)
    ).fetchone()
    assert row["active"] is False
    assert row["triggered_at"] is not None

    # a further price update must not re-fire the now-inactive alert
    result_3 = storage.upsert_offer_and_record_price(
        conn, product_id=product_id, merchant_id=merchant_id, merchant_product_id="M-1",
        price=Decimal("799.00"), currency="EUR", old_price=Decimal("829.00"), shipping_cost=None,
        availability="IN_STOCK", condition="NEW", url="https://x.example/1", image_url=None,
        source_url="https://x.example/1",
    )
    assert result_3["fired_alerts"] == []


def test_alert_unaffected_by_unrelated_product_price_changes(conn):
    storage = OfferStorage(StorageConfig(dsn=DSN))
    product_id = _make_product(conn)
    other_product_id = _make_product(conn)
    merchant_id = _make_merchant(conn, f"alert-merchant-{uuid.uuid4().hex[:8]}.example")
    user_id = _make_user(conn)

    conn.execute(
        "INSERT INTO price_alerts (user_id, product_id, target_price) VALUES (%s, %s, %s)",
        (user_id, product_id, Decimal("100.00")),
    )

    result = storage.upsert_offer_and_record_price(
        conn, product_id=other_product_id, merchant_id=merchant_id, merchant_product_id="M-2",
        price=Decimal("50.00"), currency="EUR", old_price=None, shipping_cost=None,
        availability="IN_STOCK", condition="NEW", url="https://x.example/2", image_url=None,
        source_url="https://x.example/2",
    )
    assert result["fired_alerts"] == []
