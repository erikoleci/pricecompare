"""
Automated merchant audit tool (spec sections 3 & 38).

Runs the 24-point compliance/discovery checklist against a merchant domain
and produces a JSON report. This is a READ-ONLY reconnaissance tool:

  - It NEVER fetches a URL that robots.txt disallows for our user agent.
  - It NEVER attempts to bypass CAPTCHAs, logins, or anti-bot measures.
  - It does not guess "hidden" feed/API paths that are not disclosed via
    robots.txt or linked from an allowed page - undisclosed endpoint
    guessing is out of scope, this is discovery of what a normal browser/
    crawler would be told it may access.
  - The ToS check is NOT automated interpretation: this tool only locates
    and saves the raw ToS text (if linked) for a human to actually read.
    Legal interpretation of a ToS is a human judgment call, not something
    this script decides. is_supported must still be flipped by a human.

Usage:
    python -m crawler.tools.merchant_audit --domain neptun.al [--base-url https://www.neptun.al]
    python -m crawler.tools.merchant_audit --all-pending   # reads db/004_al_merchants_pending.sql domains

Output: crawler/tools/audit_reports/<domain>.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse
import urllib.robotparser as robotparser

import httpx

USER_AGENT = "PriceCompareBot/0.1 (+https://pricecompare.example/bot; audit-only, read-only)"
TIMEOUT = 15.0
REPORT_DIR = Path(__file__).parent / "audit_reports"

TOS_LINK_PATTERN = re.compile(
    r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>[^<]*'
    r'(terms of (service|use)|kushtet e sh[eë]rbimit|kushtet e p[eë]rdorimit|t\&c)',
    re.IGNORECASE,
)
SITEMAP_HINT_PATHS = ["/sitemap.xml", "/sitemap_index.xml"]
JSONLD_PATTERN = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
PRODUCT_TYPES = {"Product", "IndividualProduct"}


@dataclass
class AuditReport:
    domain: str
    base_url: str
    audited_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # 1-2 robots.txt / ToS
    robots_txt_url: Optional[str] = None
    robots_txt_fetched: bool = False
    robots_txt_disallow_all: Optional[bool] = None
    robots_crawl_delay: Optional[float] = None
    tos_url_found: Optional[str] = None
    tos_fetched: bool = False
    tos_needs_human_review: bool = True  # always true - never auto-decided

    # 3-4 discoverable pages / sitemap
    homepage_allowed: Optional[bool] = None
    homepage_fetched: bool = False
    category_links_found: int = 0
    sitemap_urls_declared_in_robots: list[str] = field(default_factory=list)
    sitemap_reachable: list[str] = field(default_factory=list)
    sitemap_disallowed: list[str] = field(default_factory=list)

    # 5-6 structured data / feeds
    jsonld_found_on_homepage: bool = False
    jsonld_product_types_seen: list[str] = field(default_factory=list)
    product_feed_declared_in_robots: list[str] = field(default_factory=list)

    # 7-8 pagination / product pages
    pagination_pattern_detected: Optional[str] = None
    sample_product_urls: list[str] = field(default_factory=list)

    # 9-22, evaluated per sampled product page's JSON-LD (aggregated booleans)
    fields_seen_in_jsonld: dict[str, bool] = field(default_factory=lambda: {
        "price": False,
        "old_price": False,
        "discount": False,
        "stock_availability": False,
        "sku": False,
        "ean_gtin": False,
        "brand": False,
        "model_or_mpn": False,
        "specifications": False,
        "description": False,
        "images": False,
        "reviews_rating": False,
        "warranty": False,
        "shipping": False,
    })

    # 23-24 provenance - always guaranteed by connector layer, noted here for completeness
    source_url_capturable: bool = True
    scrape_timestamp_capturable: bool = True

    notes: list[str] = field(default_factory=list)
    blocked_reason: Optional[str] = None


class MerchantAuditor:
    def __init__(self, domain: str, base_url: Optional[str] = None):
        self.domain = domain
        self.base_url = (base_url or f"https://www.{domain}").rstrip("/")
        self.report = AuditReport(domain=domain, base_url=self.base_url)
        self._rp = robotparser.RobotFileParser()

    async def run(self) -> AuditReport:
        async with httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT, follow_redirects=True
        ) as client:
            robots_ok = await self._check_robots(client)
            if not robots_ok:
                self.report.blocked_reason = (
                    "robots.txt disallows all crawling for this user agent, or could "
                    "not be fetched - stopping here per spec section 3."
                )
                return self.report

            await self._check_sitemaps(client)
            await self._check_homepage(client, tos_hint=True)
            await self._sample_product_pages(client)

        return self.report

    async def _check_robots(self, client: httpx.AsyncClient) -> bool:
        robots_url = urljoin(self.base_url + "/", "robots.txt")
        self.report.robots_txt_url = robots_url
        try:
            resp = await client.get(robots_url)
        except httpx.HTTPError as exc:
            self.report.notes.append(f"robots.txt fetch failed: {exc!r}")
            return False

        if resp.status_code >= 400:
            self.report.notes.append(f"robots.txt returned HTTP {resp.status_code}")
            return False

        self.report.robots_txt_fetched = True
        self._rp.parse(resp.text.splitlines())

        # crawl-delay (best effort, RobotFileParser exposes this per-agent)
        try:
            delay = self._rp.crawl_delay(USER_AGENT) or self._rp.crawl_delay("*")
            self.report.robots_crawl_delay = float(delay) if delay else None
        except Exception:
            pass

        # sitemap directives
        try:
            self.report.sitemap_urls_declared_in_robots = list(self._rp.site_maps() or [])
        except Exception:
            pass

        allowed_root = self._rp.can_fetch(USER_AGENT, self.base_url + "/")
        self.report.robots_txt_disallow_all = not allowed_root
        if not allowed_root:
            self.report.notes.append("robots.txt disallows '/' for our user agent.")
        return allowed_root

    def _allowed(self, url: str) -> bool:
        try:
            return self._rp.can_fetch(USER_AGENT, url)
        except Exception:
            return False

    async def _check_sitemaps(self, client: httpx.AsyncClient) -> None:
        candidates = list(self.report.sitemap_urls_declared_in_robots)
        for path in SITEMAP_HINT_PATHS:
            candidates.append(urljoin(self.base_url + "/", path.lstrip("/")))
        seen = set()
        for url in candidates:
            if url in seen:
                continue
            seen.add(url)
            if not self._allowed(url):
                self.report.sitemap_disallowed.append(url)
                continue
            try:
                resp = await client.get(url)
                if resp.status_code < 400 and (
                    "xml" in resp.headers.get("content-type", "") or "<urlset" in resp.text[:500]
                    or "<sitemapindex" in resp.text[:500]
                ):
                    self.report.sitemap_reachable.append(url)
            except httpx.HTTPError as exc:
                self.report.notes.append(f"sitemap fetch failed for {url}: {exc!r}")

    async def _check_homepage(self, client: httpx.AsyncClient, tos_hint: bool = False) -> None:
        url = self.base_url + "/"
        self.report.homepage_allowed = self._allowed(url)
        if not self.report.homepage_allowed:
            self.report.notes.append("Homepage disallowed by robots.txt - skipping page-level checks.")
            return
        try:
            resp = await client.get(url)
        except httpx.HTTPError as exc:
            self.report.notes.append(f"homepage fetch failed: {exc!r}")
            return

        self.report.homepage_fetched = resp.status_code < 400
        html = resp.text

        self.report.category_links_found = len(
            re.findall(r'href=["\'][^"\']*/(category|categories|kategoria|produkte)[^"\']*["\']', html, re.I)
        )

        if tos_hint:
            m = TOS_LINK_PATTERN.search(html)
            if m:
                self.report.tos_url_found = urljoin(url, m.group(1))

        for block in JSONLD_PATTERN.findall(html):
            self.report.jsonld_found_on_homepage = True
            self._collect_jsonld_types(block[0] if isinstance(block, tuple) else block)

    def _collect_jsonld_types(self, raw: str) -> None:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            t = item.get("@type")
            types = t if isinstance(t, list) else [t]
            for t_ in types:
                if t_ and t_ not in self.report.jsonld_product_types_seen:
                    self.report.jsonld_product_types_seen.append(t_)

    async def _sample_product_pages(self, client: httpx.AsyncClient, limit: int = 3) -> None:
        """Best-effort: only follows links already present on an allowed page,
        never guesses product URLs. Evaluates JSON-LD Product schema fields."""
        url = self.base_url + "/"
        if not self._allowed(url):
            return
        try:
            resp = await client.get(url)
        except httpx.HTTPError:
            return
        html = resp.text

        product_link_pattern = re.compile(
            r'href=["\']([^"\']*/(product|produkt|item|p)/[^"\']+)["\']', re.I
        )
        candidates = []
        for match in product_link_pattern.finditer(html):
            candidate = urljoin(url, match.group(1))
            if urlparse(candidate).netloc == urlparse(self.base_url).netloc and candidate not in candidates:
                candidates.append(candidate)
            if len(candidates) >= limit * 3:
                break

        for candidate in candidates:
            if len(self.report.sample_product_urls) >= limit:
                break
            if not self._allowed(candidate):
                continue
            try:
                presp = await client.get(candidate)
            except httpx.HTTPError:
                continue
            if presp.status_code >= 400:
                continue
            self.report.sample_product_urls.append(candidate)
            self._evaluate_product_fields(presp.text)

        if not self.report.sample_product_urls:
            self.report.notes.append(
                "No product-detail links matched heuristics from the homepage alone; "
                "a category page would need to be crawled first (out of scope for this "
                "quick audit)."
            )

    def _evaluate_product_fields(self, html: str) -> None:
        for block in JSONLD_PATTERN.findall(html):
            raw = block[0] if isinstance(block, tuple) else block
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                t = item.get("@type")
                types = set(t if isinstance(t, list) else [t])
                if not types & PRODUCT_TYPES:
                    continue
                self._mark_fields_from_product_jsonld(item)

    def _mark_fields_from_product_jsonld(self, item: dict) -> None:
        f = self.report.fields_seen_in_jsonld
        offers = item.get("offers")
        offer = (offers[0] if isinstance(offers, list) and offers else offers) or {}

        if isinstance(offer, dict):
            if offer.get("price") is not None:
                f["price"] = True
            if offer.get("priceSpecification") or offer.get("highPrice"):
                f["old_price"] = True
            if offer.get("availability"):
                f["stock_availability"] = True
            if offer.get("sku") or item.get("sku"):
                f["sku"] = True
            if offer.get("shippingDetails"):
                f["shipping"] = True
            if offer.get("warranty") or item.get("warranty"):
                f["warranty"] = True
        if item.get("gtin") or item.get("gtin13") or item.get("gtin12") or item.get("gtin8") or item.get("gtin14"):
            f["ean_gtin"] = True
        if item.get("brand"):
            f["brand"] = True
        if item.get("model") or item.get("mpn"):
            f["model_or_mpn"] = True
        if item.get("additionalProperty"):
            f["specifications"] = True
        if item.get("description"):
            f["description"] = True
        if item.get("image"):
            f["images"] = True
        if item.get("aggregateRating") or item.get("review"):
            f["reviews_rating"] = True
        # "discount" has no dedicated schema.org field - inferred elsewhere
        # (e.g. old_price present + price present) rather than a single flag.
        if f["price"] and f["old_price"]:
            f["discount"] = True


async def audit_one(domain: str, base_url: Optional[str] = None) -> AuditReport:
    auditor = MerchantAuditor(domain, base_url)
    report = await auditor.run()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORT_DIR / f"{domain}.json"
    out_path.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    return report


def _print_summary(report: AuditReport) -> None:
    print(f"\n=== {report.domain} ===")
    if report.blocked_reason:
        print(f"  BLOCKED: {report.blocked_reason}")
        return
    print(f"  robots.txt: {report.robots_txt_url} (fetched={report.robots_txt_fetched}, "
          f"disallow_all={report.robots_txt_disallow_all}, crawl_delay={report.robots_crawl_delay})")
    print(f"  sitemap reachable: {report.sitemap_reachable or 'none found'}")
    print(f"  ToS link found: {report.tos_url_found or 'not found - needs manual search'} "
          f"(NEEDS HUMAN REVIEW)")
    print(f"  JSON-LD on homepage: {report.jsonld_found_on_homepage} "
          f"({report.jsonld_product_types_seen})")
    print(f"  sample product URLs sampled: {len(report.sample_product_urls)}")
    for k, v in report.fields_seen_in_jsonld.items():
        print(f"    - {k}: {'OK' if v else 'not detected'}")
    if report.notes:
        print("  notes:")
        for n in report.notes:
            print(f"    * {n}")


async def _main_async(args: argparse.Namespace) -> None:
    if args.domain:
        report = await audit_one(args.domain, args.base_url)
        _print_summary(report)
    elif args.domains_file:
        domains = [
            line.strip() for line in Path(args.domains_file).read_text().splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        for d in domains:
            report = await audit_one(d)
            _print_summary(report)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", help="Single domain to audit, e.g. neptun.al")
    parser.add_argument("--base-url", help="Override base URL, e.g. https://www.neptun.al")
    parser.add_argument(
        "--domains-file",
        help="Path to a text file with one domain per line (# comments allowed)",
    )
    args = parser.parse_args()
    if not args.domain and not args.domains_file:
        parser.error("provide --domain or --domains-file")
        sys.exit(2)
    asyncio.run(_main_async(args))


if __name__ == "__main__":
    main()
