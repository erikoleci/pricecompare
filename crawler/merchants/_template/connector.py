"""
TEMPLATE merchant connector.

Copy this folder to crawler/merchants/<merchant_slug>/ to onboard a new
merchant. Before writing a single line of extraction logic:

  1. Read the merchant's robots.txt and Terms of Service.
  2. Record findings in the `merchant_sources` DB row (allowed_by_robots,
     tos_reviewed, tos_notes, crawl_delay_seconds, max_requests_per_min,
     is_supported).
  3. Only set is_supported=true once (1) and (2) are done. Until then this
     connector must not be scheduled (spec section 3 + 38).

This template deliberately raises NotImplementedError everywhere - it is a
scaffold, not a working scraper for any real site.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Optional

from playwright.async_api import async_playwright

from crawler.core.compliance import ComplianceGate, MerchantPolicy
from crawler.interfaces.merchant_connector import (
    MerchantConnector,
    RawImage,
    RawOffer,
    RawSpecification,
)


class TemplateConnector(MerchantConnector):
    domain = "example-merchant.com"

    def __init__(self, policy: MerchantPolicy, gate: ComplianceGate) -> None:
        self.policy = policy
        self.gate = gate

    async def discover_products(self, category: Optional[str] = None) -> Iterable[str]:
        """Enumerate product URLs from category/listing pages.
        Must only follow links reachable via a compliant crawl path
        (no login-gated listings, no bypassing pagination limits set by ToS)."""
        raise NotImplementedError("Implement per-merchant category discovery")

    async def _get_page_html(self, url: str) -> str:
        if not self.gate.is_allowed(self.policy, url):
            raise PermissionError(f"Crawling disallowed for {url} (robots.txt / not marked supported)")
        self.gate.wait_for_slot(self.policy)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(user_agent="PriceCompareBot/1.0 (+https://pricecompare.example/bot)")
            await page.goto(url, wait_until="domcontentloaded")
            html = await page.content()
            await browser.close()
            return html

    async def fetch_product(self, url: str) -> RawOffer:
        html = await self._get_page_html(url)
        return RawOffer(
            merchant_domain=self.domain,
            merchant_product_id=self._extract_merchant_product_id(html),
            title=self._extract_title(html),
            url=url,
            price=self.extract_price(html),
            currency="EUR",
            shipping_cost=self._extract_shipping_cost(html),  # None if not shown on page
            availability=self.extract_availability(html),
            specifications=self.extract_specifications(html),
            images=self.extract_images(html),
            source_url=url,
        )

    # --- Extraction methods: implement with real selectors per merchant ---

    def extract_price(self, page_content: str) -> Decimal:
        raise NotImplementedError

    def extract_availability(self, page_content: str) -> str:
        raise NotImplementedError

    def extract_specifications(self, page_content: str) -> list[RawSpecification]:
        raise NotImplementedError

    def extract_images(self, page_content: str) -> list[RawImage]:
        raise NotImplementedError

    def _extract_title(self, page_content: str) -> str:
        raise NotImplementedError

    def _extract_merchant_product_id(self, page_content: str) -> str:
        raise NotImplementedError

    def _extract_shipping_cost(self, page_content: str) -> Optional[Decimal]:
        """Return None (not 0) when shipping cost isn't explicitly shown - never assume free (section 6)."""
        raise NotImplementedError
