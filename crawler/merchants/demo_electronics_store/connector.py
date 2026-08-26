"""
Reference connector demonstrating the full extraction pattern from
crawler/interfaces/merchant_connector.py against a fixture page
(tests/fixtures/demo_store_product.html).

IMPORTANT: "demo-electronics.example" is a fictional placeholder domain, not
a real merchant. This connector exists to prove the pipeline end-to-end
(parse -> normalize -> match -> store) with real, runnable code and
passing tests. Before pointing a copy of this connector at any real
merchant, follow the checklist in crawler/merchants/_template/connector.py:
review that merchant's actual robots.txt and Terms of Service, and only
mark it `is_supported=true` in `merchant_sources` once that review is done.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Optional

from bs4 import BeautifulSoup

from crawler.core.compliance import ComplianceGate, MerchantPolicy
from crawler.interfaces.merchant_connector import (
    MerchantConnector,
    RawImage,
    RawOffer,
    RawSpecification,
)


class DemoElectronicsStoreConnector(MerchantConnector):
    domain = "demo-electronics.example"

    def __init__(self, policy: MerchantPolicy, gate: ComplianceGate) -> None:
        self.policy = policy
        self.gate = gate

    async def discover_products(self, category: Optional[str] = None) -> Iterable[str]:
        # A real connector would crawl category/listing pages here, respecting
        # pagination limits and only following links robots.txt permits.
        raise NotImplementedError("Not needed for the fixture-based demo/tests")

    async def fetch_product(self, url: str) -> RawOffer:
        # A real connector fetches page_content via Playwright through
        # self.gate.wait_for_slot(...) first. The fixture test calls
        # parse_offer() directly with saved HTML instead, so no network is
        # needed to prove the extraction logic works.
        raise NotImplementedError("Use parse_offer() with fixture HTML for testing")

    def parse_offer(self, page_content: str, url: str) -> RawOffer:
        soup = BeautifulSoup(page_content, "lxml")
        product_div = soup.select_one(".product-page")

        return RawOffer(
            merchant_domain=self.domain,
            merchant_product_id=product_div["data-product-id"],
            title=soup.select_one(".product-title").get_text(strip=True),
            url=url,
            price=self.extract_price(page_content),
            currency=soup.select_one(".price")["data-currency"],
            old_price=self._extract_old_price(soup),
            shipping_cost=self._extract_shipping_cost(soup),
            availability=self.extract_availability(page_content),
            ean=self._text_or_none(soup, ".ean"),
            mpn=self._text_or_none(soup, ".mpn"),
            specifications=self.extract_specifications(page_content),
            images=self.extract_images(page_content),
            source_url=url,
        )

    def extract_price(self, page_content: str) -> Decimal:
        soup = BeautifulSoup(page_content, "lxml")
        raw = soup.select_one(".price").get_text(strip=True)
        return self._parse_money(raw)

    def extract_availability(self, page_content: str) -> str:
        soup = BeautifulSoup(page_content, "lxml")
        el = soup.select_one(".availability")
        if el is None:
            return "UNKNOWN"
        classes = el.get("class", [])
        if "in-stock" in classes:
            return "IN_STOCK"
        if "out-of-stock" in classes:
            return "OUT_OF_STOCK"
        if "preorder" in classes:
            return "PREORDER"
        return "UNKNOWN"

    def extract_specifications(self, page_content: str) -> list[RawSpecification]:
        soup = BeautifulSoup(page_content, "lxml")
        specs = []
        for li in soup.select(".specifications li"):
            specs.append(RawSpecification(
                key=li["data-key"],
                value=li.get_text(strip=True),
                unit=li.get("data-unit"),
            ))
        return specs

    def extract_images(self, page_content: str) -> list[RawImage]:
        soup = BeautifulSoup(page_content, "lxml")
        return [
            RawImage(url=img["src"], position=i)
            for i, img in enumerate(soup.select(".product-image"))
        ]

    # --- helpers ---

    @staticmethod
    def _parse_money(raw: str) -> Decimal:
        cleaned = raw.replace("€", "").replace("$", "").replace(",", "").strip()
        return Decimal(cleaned)

    def _extract_old_price(self, soup: BeautifulSoup) -> Optional[Decimal]:
        el = soup.select_one(".old-price")
        return self._parse_money(el.get_text(strip=True)) if el else None

    def _extract_shipping_cost(self, soup: BeautifulSoup) -> Optional[Decimal]:
        """Returns None (not 0) when the page doesn't show a shipping cost - never assume free (section 6)."""
        el = soup.select_one(".shipping-cost")
        return self._parse_money(el.get_text(strip=True)) if el else None

    @staticmethod
    def _text_or_none(soup: BeautifulSoup, selector: str) -> Optional[str]:
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else None
