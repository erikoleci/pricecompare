"""
Standard interface every merchant connector must implement.

Every connector returns data shaped as the RawOffer dataclass below - the
normalizer (crawler/normalizers/) is responsible for turning that into the
canonical Product/Offer models the backend understands (spec section 5-6).

A connector MUST NOT attempt to bypass CAPTCHAs, logins, anti-bot measures,
or access controls of any kind (spec section 3). It must respect the
policy declared in the merchant's `merchant_sources` DB row (robots.txt,
crawl-delay, requests/min) - that policy is enforced by the scheduler/
rate limiter, not by the connector itself, so connectors stay simple.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable, Optional


@dataclass
class RawImage:
    url: str
    position: int = 0


@dataclass
class RawSpecification:
    key: str
    value: str
    unit: Optional[str] = None


@dataclass
class RawReview:
    author_name: Optional[str]
    rating: float
    title: Optional[str]
    text: Optional[str]
    review_date: Optional[str]
    verified: bool = False


@dataclass
class RawOffer:
    """One merchant's listing for one product, as scraped - not yet matched to a canonical Product."""

    merchant_domain: str
    merchant_product_id: str
    title: str
    url: str

    price: Decimal
    currency: str
    old_price: Optional[Decimal] = None
    shipping_cost: Optional[Decimal] = None  # None = unknown; NEVER default to 0 (spec section 6)

    availability: str = "UNKNOWN"  # IN_STOCK, OUT_OF_STOCK, PREORDER, UNKNOWN
    condition: str = "NEW"

    brand: Optional[str] = None
    model: Optional[str] = None
    ean: Optional[str] = None
    gtin: Optional[str] = None
    sku: Optional[str] = None
    mpn: Optional[str] = None

    description: Optional[str] = None
    category_hint: Optional[str] = None

    images: list[RawImage] = field(default_factory=list)
    specifications: list[RawSpecification] = field(default_factory=list)
    reviews: list[RawReview] = field(default_factory=list)

    # Provenance - required on every record (spec section 39)
    source_url: str = ""
    source_type: str = "SCRAPER"
    scraped_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MerchantConnector(ABC):
    """Every merchant integration under crawler/merchants/<merchant>/ implements this."""

    #: must match the `domain` column of the merchants table
    domain: str

    @abstractmethod
    async def discover_products(self, category: Optional[str] = None) -> Iterable[str]:
        """Yield product URLs to crawl. Must only enumerate pages allowed by robots.txt."""
        raise NotImplementedError

    @abstractmethod
    async def fetch_product(self, url: str) -> RawOffer:
        """Fetch and parse a single product page into a RawOffer."""
        raise NotImplementedError

    @abstractmethod
    def extract_price(self, page_content: str) -> Decimal:
        raise NotImplementedError

    @abstractmethod
    def extract_availability(self, page_content: str) -> str:
        raise NotImplementedError

    def extract_reviews(self, page_content: str) -> list[RawReview]:
        """Optional - only override if the merchant's own ToS/robots.txt permits review extraction."""
        return []

    @abstractmethod
    def extract_specifications(self, page_content: str) -> list[RawSpecification]:
        raise NotImplementedError

    @abstractmethod
    def extract_images(self, page_content: str) -> list[RawImage]:
        raise NotImplementedError
