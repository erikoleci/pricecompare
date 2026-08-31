"""
celular.al connector - schema.org JSON-LD based extraction.

WHY JSON-LD instead of hand-picked CSS selectors: db/006_al_merchants_verified.sql
confirms celular.al is server-rendered (Astro/SSR - full HTML in the initial
response, unlike globe.al/gjirafa50.com which are client-rendered SPAs), but
no session so far has been able to actually fetch a real product page's HTML
(web_fetch in the chat tooling only allows URLs already seen in a search
result, and this sandbox's network egress doesn't reach celular.al either).
Writing CSS selectors against *guessed* HTML structure would produce code
that silently breaks or, worse, silently extracts the wrong thing on a real
page - worse than not writing it at all. JSON-LD Product markup is a
public, standardized contract (schema.org) that doesn't require guessing a
specific site's class names, and most modern storefronts (including
WooCommerce/Astro-based ones) emit it for SEO. This connector extracts from
that markup; if celular.al's actual pages don't carry complete JSON-LD for a
given field, that field will simply come back None/UNKNOWN rather than a
wrong value - see _MISSING_FIELD_NOTE below.

STILL NOT LIVE: is_supported stays false in merchant_sources until a human
(or an agent with real, unrestricted browser access) actually opens
https://www.celular.al/robots.txt and https://celular.al/kushtet-e-pergjithshme
and records the outcome per spec section 3 & 38. ComplianceGate.is_allowed()
enforces that at run time regardless - this connector cannot run against a
merchant whose merchant_sources.is_supported is false.

discover_products() is intentionally left NotImplementedError: category/
listing page URLs need to be confirmed against the real site structure
first (this connector was written blind, per the note above) - filling
that in is a five-minute job once someone with browser access opens
https://celular.al/products/ and confirms the pagination/listing pattern.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from typing import Iterable, Optional

from crawler.core.compliance import ComplianceGate, MerchantPolicy
from crawler.interfaces.merchant_connector import (
    MerchantConnector,
    RawImage,
    RawOffer,
    RawReview,
    RawSpecification,
)

_JSONLD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
_PRODUCT_TYPES = {"Product", "IndividualProduct"}

# Fields this connector cannot fill from JSON-LD alone even on a real fetch,
# because schema.org Product has no dedicated slot for them. A future pass
# with real page access should add HTML fallbacks for these specifically:
_MISSING_FIELD_NOTE = "warranty, discount_percent (derivable from old_price+price once both are confirmed present)"


class CelularAlConnector(MerchantConnector):
    domain = "celular.al"

    def __init__(self, policy: MerchantPolicy, gate: ComplianceGate) -> None:
        self.policy = policy
        self.gate = gate

    async def discover_products(self, category: Optional[str] = None) -> Iterable[str]:
        raise NotImplementedError(
            "Category/listing URL pattern not yet confirmed against the real site - "
            "see module docstring. Needs one live session with real browser/fetch access."
        )

    async def _get_page_html(self, url: str) -> str:
        if not self.gate.is_allowed(self.policy, url):
            raise PermissionError(f"Crawling disallowed for {url} (robots.txt / not marked supported)")
        self.gate.wait_for_slot(self.policy)

        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(
                user_agent="PriceCompareBot/1.0 (+https://pricecompare.example/bot)"
            )
            await page.goto(url, wait_until="domcontentloaded")
            html = await page.content()
            await browser.close()
            return html

    async def fetch_product(self, url: str) -> RawOffer:
        html = await self._get_page_html(url)
        return self.parse_offer(html, url)

    # ------------------------------------------------------------------
    # Parsing (synchronous, testable against saved/fixture HTML without
    # a live fetch - same pattern as demo_electronics_store.parse_offer)
    # ------------------------------------------------------------------
    def parse_offer(self, page_content: str, url: str) -> RawOffer:
        product = self._find_product_jsonld(page_content)
        if product is None:
            raise ValueError(
                f"No schema.org Product JSON-LD found on {url}. Either the page "
                "doesn't carry structured data, or the real page structure differs "
                "from what this connector assumes - needs a live re-check."
            )

        offers = product.get("offers")
        offer = (offers[0] if isinstance(offers, list) and offers else offers) or {}
        if not isinstance(offer, dict):
            offer = {}

        price = self.extract_price(page_content)
        old_price = self._extract_old_price(offer)

        return RawOffer(
            merchant_domain=self.domain,
            merchant_product_id=str(offer.get("sku") or product.get("sku") or product.get("productID") or ""),
            title=str(product.get("name", "")).strip(),
            url=url,
            price=price,
            currency=str(offer.get("priceCurrency", "EUR")),
            old_price=old_price,
            shipping_cost=self._extract_shipping_cost(offer),
            availability=self.extract_availability(page_content),
            sku=self._none_if_blank(offer.get("sku") or product.get("sku")),
            ean=self._extract_gtin(product),
            gtin=self._extract_gtin(product),
            mpn=self._none_if_blank(product.get("mpn")),
            brand=self._extract_brand(product),
            model=self._none_if_blank(product.get("model")),
            description=self._none_if_blank(product.get("description")),
            specifications=self.extract_specifications(page_content),
            images=self.extract_images(page_content),
            reviews=self.extract_reviews(page_content),
            source_url=url,
        )

    def extract_price(self, page_content: str) -> Decimal:
        product = self._find_product_jsonld(page_content)
        if product is None:
            raise ValueError("No Product JSON-LD found - cannot extract price")
        offers = product.get("offers")
        offer = (offers[0] if isinstance(offers, list) and offers else offers) or {}
        raw_price = offer.get("price") if isinstance(offer, dict) else None
        if raw_price is None:
            raise ValueError("Product JSON-LD present but has no offers.price")
        return self._to_decimal(raw_price)

    def extract_availability(self, page_content: str) -> str:
        product = self._find_product_jsonld(page_content)
        if product is None:
            return "UNKNOWN"
        offers = product.get("offers")
        offer = (offers[0] if isinstance(offers, list) and offers else offers) or {}
        avail = str(offer.get("availability", "")) if isinstance(offer, dict) else ""
        avail = avail.rsplit("/", 1)[-1]  # "https://schema.org/InStock" -> "InStock"
        mapping = {
            "InStock": "IN_STOCK",
            "LimitedAvailability": "IN_STOCK",
            "OutOfStock": "OUT_OF_STOCK",
            "SoldOut": "OUT_OF_STOCK",
            "PreOrder": "PREORDER",
            "PreSale": "PREORDER",
            "BackOrder": "PREORDER",
        }
        return mapping.get(avail, "UNKNOWN")

    def extract_specifications(self, page_content: str) -> list[RawSpecification]:
        product = self._find_product_jsonld(page_content)
        if product is None:
            return []
        specs = []
        for prop in product.get("additionalProperty", []) or []:
            if not isinstance(prop, dict):
                continue
            name = prop.get("name")
            value = prop.get("value")
            if name is None or value is None:
                continue
            specs.append(RawSpecification(key=str(name), value=str(value), unit=prop.get("unitText")))
        return specs

    def extract_images(self, page_content: str) -> list[RawImage]:
        product = self._find_product_jsonld(page_content)
        if product is None:
            return []
        raw_images = product.get("image")
        if raw_images is None:
            return []
        if isinstance(raw_images, str):
            raw_images = [raw_images]
        images = []
        for i, img in enumerate(raw_images):
            if isinstance(img, str):
                images.append(RawImage(url=img, position=i))
            elif isinstance(img, dict) and img.get("url"):
                images.append(RawImage(url=img["url"], position=i))
        return images

    def extract_reviews(self, page_content: str) -> list[RawReview]:
        # Only extracts reviews if celular.al's own JSON-LD includes a `review`
        # array (i.e. the merchant is already publishing them as public
        # structured data for search engines) - never scrapes reviews from a
        # source that hasn't already made them part of the public page markup.
        # Still gated: this is only ever called if is_supported=true, i.e.
        # after the robots.txt/ToS review spec section 3 requires.
        product = self._find_product_jsonld(page_content)
        if product is None:
            return []
        raw_reviews = product.get("review")
        if not raw_reviews:
            return []
        if isinstance(raw_reviews, dict):
            raw_reviews = [raw_reviews]

        reviews = []
        for r in raw_reviews:
            if not isinstance(r, dict):
                continue
            rating_val = (r.get("reviewRating") or {}).get("ratingValue")
            if rating_val is None:
                continue
            author = r.get("author")
            author_name = author.get("name") if isinstance(author, dict) else author
            reviews.append(RawReview(
                author_name=self._none_if_blank(author_name),
                rating=float(rating_val),
                title=self._none_if_blank(r.get("name")),
                text=self._none_if_blank(r.get("reviewBody")),
                review_date=self._none_if_blank(r.get("datePublished")),
                verified=False,  # JSON-LD has no standard "verified purchase" field
            ))
        return reviews

    # --- helpers ---

    @staticmethod
    def _find_product_jsonld(page_content: str) -> Optional[dict]:
        for match in _JSONLD_RE.findall(page_content):
            try:
                data = json.loads(match)
            except json.JSONDecodeError:
                continue
            items = data if isinstance(data, list) else [data]
            # also handle @graph-wrapped JSON-LD (common with SEO plugins)
            flattened = []
            for item in items:
                if isinstance(item, dict) and "@graph" in item:
                    flattened.extend(item["@graph"])
                else:
                    flattened.append(item)
            for item in flattened:
                if not isinstance(item, dict):
                    continue
                t = item.get("@type")
                types = set(t if isinstance(t, list) else [t])
                if types & _PRODUCT_TYPES:
                    return item
        return None

    @staticmethod
    def _to_decimal(value) -> Decimal:
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError):
            raise ValueError(f"Could not parse price value: {value!r}")

    def _extract_old_price(self, offer: dict) -> Optional[Decimal]:
        # schema.org has no dedicated "old price" field on Offer. Some sites
        # emit it via priceSpecification.price with priceType "StrikethroughPrice",
        # or via a highPrice on an AggregateOffer - check both, else None
        # (never fabricate a discount that isn't actually shown).
        spec = offer.get("priceSpecification")
        if isinstance(spec, dict) and spec.get("price"):
            try:
                return self._to_decimal(spec["price"])
            except ValueError:
                pass
        high = offer.get("highPrice")
        if high is not None:
            try:
                return self._to_decimal(high)
            except ValueError:
                pass
        return None

    def _extract_shipping_cost(self, offer: dict) -> Optional[Decimal]:
        """Returns None (not 0) when shipping isn't in the JSON-LD - never assume free (section 6)."""
        shipping = offer.get("shippingDetails")
        if not isinstance(shipping, dict):
            return None
        rate = shipping.get("shippingRate")
        if isinstance(rate, dict) and rate.get("value") is not None:
            try:
                return self._to_decimal(rate["value"])
            except ValueError:
                return None
        return None

    @staticmethod
    def _extract_gtin(product: dict) -> Optional[str]:
        for key in ("gtin13", "gtin", "gtin12", "gtin14", "gtin8"):
            value = product.get(key)
            if value:
                return str(value)
        return None

    @staticmethod
    def _extract_brand(product: dict) -> Optional[str]:
        brand = product.get("brand")
        if isinstance(brand, dict):
            return brand.get("name")
        if isinstance(brand, str):
            return brand
        return None

    @staticmethod
    def _none_if_blank(value) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
