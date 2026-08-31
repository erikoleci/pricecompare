"""
Tests the JSON-LD extraction logic in CelularAlConnector against a synthetic
fixture (see fixtures/celular_al_product_jsonld.html docstring - it's a
standard schema.org Product example, NOT captured from the real site, since
no session so far has had real fetch access to celular.al). These tests
prove the *extraction code* is correct; they do not and cannot prove the
real celular.al pages actually carry this markup - that still needs a live
check before is_supported is ever flipped to true (spec section 3 & 38).
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from crawler.merchants.celular_al.connector import CelularAlConnector

FIXTURE = Path(__file__).parent / "fixtures" / "celular_al_product_jsonld.html"


def _connector() -> CelularAlConnector:
    # policy/gate aren't exercised by parse_offer() - only used by the async
    # fetch path, which needs a live/allowed URL and isn't tested here.
    return CelularAlConnector(policy=None, gate=None)  # type: ignore[arg-type]


def test_parse_offer_extracts_core_fields():
    html = FIXTURE.read_text()
    connector = _connector()
    raw = connector.parse_offer(html, url="https://celular.al/products/samsung/galaxy-s25-ultra")

    assert raw.merchant_domain == "celular.al"
    assert raw.title == "Samsung Galaxy S25 Ultra 256GB Titanium Black"
    assert raw.sku == "SGS25U-256-BLK"
    assert raw.ean == "8806095123456"
    assert raw.gtin == "8806095123456"
    assert raw.brand == "Samsung"
    assert raw.model == "SM-S938B"
    assert raw.price == Decimal("1299.00")
    assert raw.old_price == Decimal("1399.00")
    assert raw.currency == "EUR"
    assert raw.shipping_cost == Decimal("0.00")
    assert raw.availability == "IN_STOCK"
    assert "Dynamic AMOLED" in raw.description


def test_extract_specifications():
    html = FIXTURE.read_text()
    specs = _connector().extract_specifications(html)
    by_key = {s.key: (s.value, s.unit) for s in specs}
    assert by_key["Display"] == ("6.9", "inch")
    assert by_key["RAM"] == ("12", "GB")
    assert by_key["Storage"] == ("256", "GB")


def test_extract_images():
    html = FIXTURE.read_text()
    images = _connector().extract_images(html)
    assert len(images) == 2
    assert images[0].url == "https://celular.al/img/products/sgs25u-1.jpg"
    assert images[0].position == 0
    assert images[1].position == 1


def test_extract_reviews_from_jsonld():
    html = FIXTURE.read_text()
    reviews = _connector().extract_reviews(html)
    assert len(reviews) == 2
    assert reviews[0].author_name == "Genti K."
    assert reviews[0].rating == 5.0
    assert reviews[1].rating == 4.0
    assert reviews[1].review_date == "2026-05-03"


def test_missing_jsonld_raises_clear_error_not_silent_wrong_data():
    connector = _connector()
    html_without_jsonld = "<html><body><h1>No structured data here</h1></body></html>"
    try:
        connector.parse_offer(html_without_jsonld, url="https://celular.al/products/x")
        assert False, "expected ValueError when no Product JSON-LD is present"
    except ValueError as exc:
        assert "JSON-LD" in str(exc)


def test_shipping_cost_none_when_not_declared():
    """Section 6: never assume free shipping when the page simply doesn't say."""
    html = """
    <script type="application/ld+json">
    {"@type": "Product", "name": "X", "offers": {"@type": "Offer", "price": "10.00", "priceCurrency": "EUR"}}
    </script>
    """
    connector = _connector()
    raw = connector.parse_offer(html, url="https://celular.al/products/x")
    assert raw.shipping_cost is None


def test_availability_mapping():
    connector = _connector()
    for schema_value, expected in [
        ("https://schema.org/InStock", "IN_STOCK"),
        ("https://schema.org/OutOfStock", "OUT_OF_STOCK"),
        ("https://schema.org/PreOrder", "PREORDER"),
        ("https://schema.org/SomethingUnknown", "UNKNOWN"),
    ]:
        html = f"""
        <script type="application/ld+json">
        {{"@type": "Product", "name": "X", "offers": {{"@type": "Offer", "price": "10.00",
          "availability": "{schema_value}"}}}}
        </script>
        """
        assert connector.extract_availability(html) == expected
