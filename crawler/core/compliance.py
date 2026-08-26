"""
Access-compliance gate.

Every crawl request MUST pass through here first. This is the single place
that decides whether a merchant/URL may be crawled at all - connectors never
make that decision themselves. Enforces spec section 3:

  - robots.txt must explicitly allow the path
  - a per-merchant crawl-delay / requests-per-minute budget (from
    merchant_sources) is respected
  - no CAPTCHA/login/anti-bot bypass of any kind is attempted; if a fetch
    is blocked by one of those, the merchant is marked unsupported instead
    of retried with evasive techniques
"""

from __future__ import annotations

import time
import urllib.robotparser as robotparser
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass
class MerchantPolicy:
    domain: str
    base_url: str
    crawl_delay_seconds: float = 2.0
    max_requests_per_min: int = 20
    is_supported: bool = False  # must be explicitly enabled after a manual ToS/robots.txt review


class ComplianceGate:
    def __init__(self) -> None:
        self._robot_parsers: dict[str, robotparser.RobotFileParser] = {}
        self._last_request_at: dict[str, float] = {}
        self._request_window: dict[str, list[float]] = {}

    def _get_robot_parser(self, base_url: str) -> robotparser.RobotFileParser:
        if base_url not in self._robot_parsers:
            rp = robotparser.RobotFileParser()
            rp.set_url(f"{base_url.rstrip('/')}/robots.txt")
            rp.read()
            self._robot_parsers[base_url] = rp
        return self._robot_parsers[base_url]

    def is_allowed(self, policy: MerchantPolicy, url: str, user_agent: str = "PriceCompareBot") -> bool:
        if not policy.is_supported:
            return False
        rp = self._get_robot_parser(policy.base_url)
        return rp.can_fetch(user_agent, url)

    def wait_for_slot(self, policy: MerchantPolicy) -> None:
        """Blocks (cooperatively, via time.sleep) until it's safe to make another
        request under this merchant's crawl-delay AND requests-per-minute budget."""
        now = time.time()

        last = self._last_request_at.get(policy.domain)
        if last is not None:
            elapsed = now - last
            if elapsed < policy.crawl_delay_seconds:
                time.sleep(policy.crawl_delay_seconds - elapsed)

        window = self._request_window.setdefault(policy.domain, [])
        window[:] = [t for t in window if time.time() - t < 60]
        if len(window) >= policy.max_requests_per_min:
            sleep_for = 60 - (time.time() - window[0])
            if sleep_for > 0:
                time.sleep(sleep_for)
            window[:] = [t for t in window if time.time() - t < 60]

        self._last_request_at[policy.domain] = time.time()
        window.append(time.time())

    @staticmethod
    def same_domain(url: str, policy: MerchantPolicy) -> bool:
        return urlparse(url).netloc.endswith(urlparse(policy.base_url).netloc)
