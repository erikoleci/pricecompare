"""
Turns a RawOffer (whatever a connector scraped) into normalized fields ready
for product matching and storage. Pure functions only - no I/O, no DB access,
so this stays easy to unit test in isolation from any real merchant.
"""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal
from typing import Optional

from crawler.interfaces.merchant_connector import RawOffer

_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9 ]")

# Common noisy tokens that don't help matching and hurt fuzzy comparisons
_NOISE_TOKENS = {
    "new", "sealed", "original", "genuine", "official", "brand", "authentic",
}


def normalize_title(title: str) -> str:
    """Lowercase, strip accents/punctuation, collapse whitespace, drop noise tokens.
    'Apple iPhone 17 Pro 256GB Black' and 'iPhone 17 Pro 256 GB Black' both
    normalize close enough for the fuzzy-matching stage to link them (spec section 15).
    """
    text = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    text = text.lower()
    text = text.replace("gb", " gb").replace("tb", " tb")  # separate size from unit, e.g. "256gb" -> "256 gb"
    text = _NON_ALNUM_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    tokens = [t for t in text.split(" ") if t not in _NOISE_TOKENS]
    return " ".join(tokens)


def extract_storage_gb(title_or_specs: str) -> Optional[int]:
    match = re.search(r"(\d{2,4})\s?gb", title_or_specs.lower())
    if match:
        return int(match.group(1))
    match = re.search(r"(\d)\s?tb", title_or_specs.lower())
    if match:
        return int(match.group(1)) * 1024
    return None


def compute_total_price(price: Decimal, shipping_cost: Optional[Decimal]) -> Decimal:
    """total_price = price + shipping. Shipping unknown -> total == price, but the
    caller must still persist shipping_cost=None (not 0) so the UI can say "shipping unknown"
    instead of implying free shipping (spec section 6)."""
    return price + shipping_cost if shipping_cost is not None else price


def compute_discount_percent(price: Decimal, old_price: Optional[Decimal]) -> Optional[Decimal]:
    if not old_price or old_price <= 0 or old_price <= price:
        return None
    return ((old_price - price) / old_price * 100).quantize(Decimal("0.01"))


def build_identifier_candidates(raw: RawOffer) -> list[tuple[str, str]]:
    """Ordered by matching priority (spec section 15): EAN > GTIN > MPN."""
    candidates: list[tuple[str, str]] = []
    if raw.ean:
        candidates.append(("EAN", raw.ean.strip()))
    if raw.gtin:
        candidates.append(("GTIN", raw.gtin.strip()))
    if raw.mpn:
        candidates.append(("MPN", raw.mpn.strip()))
    if raw.sku:
        candidates.append(("SKU", raw.sku.strip()))
    return candidates
