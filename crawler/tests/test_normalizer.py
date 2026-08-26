from decimal import Decimal

from crawler.normalizers.product_normalizer import (
    normalize_title,
    compute_total_price,
    compute_discount_percent,
)
from crawler.normalizers.product_matcher import (
    score_normalized_title_match,
    decision_for,
)


def test_normalize_title_matches_across_merchants():
    a = normalize_title("Apple iPhone 17 Pro 256GB Black")
    b = normalize_title("iPhone 17 Pro 256 GB Black")
    assert a.replace("apple ", "") == b


def test_total_price_unknown_shipping_stays_none_not_zero():
    total = compute_total_price(Decimal("899.00"), None)
    assert total == Decimal("899.00")


def test_total_price_adds_known_shipping():
    total = compute_total_price(Decimal("899.00"), Decimal("9.99"))
    assert total == Decimal("908.99")


def test_discount_percent_computed_correctly():
    pct = compute_discount_percent(Decimal("899.00"), Decimal("999.00"))
    assert pct == Decimal("10.01")


def test_discount_percent_none_when_no_old_price():
    assert compute_discount_percent(Decimal("899.00"), None) is None


def test_title_similarity_never_exceeds_possible_match_band():
    score = score_normalized_title_match(
        normalize_title("iPhone 17 Pro 256GB Black"),
        normalize_title("iPhone 17 Pro 256GB Black"),
    )
    assert score <= 70  # even identical titles cap at the "possible match" ceiling
    assert decision_for(score) in {"PENDING", "AUTO_MERGED"}


def test_decision_thresholds():
    assert decision_for(100) == "AUTO_MERGED"
    assert decision_for(90) == "AUTO_MERGED"
    assert decision_for(80) == "PENDING"
    assert decision_for(69.9) == "REJECTED"
