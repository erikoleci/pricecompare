"""
Decides how often each product/merchant should be re-crawled.

Priority tiers (spec section 31):
  HIGH   - popular products, products with frequent price changes
  MEDIUM - normal products (default)
  LOW    - products with little traffic/activity

This module only computes priority + next-crawl time; the actual job queue
(e.g. a Postgres-backed `crawler_jobs` table, or Redis-backed queue) enqueues
work based on what this returns.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum


class Priority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


_REFRESH_INTERVAL = {
    Priority.HIGH: timedelta(hours=4),
    Priority.MEDIUM: timedelta(hours=24),
    Priority.LOW: timedelta(days=7),
}


@dataclass
class ProductActivitySignal:
    product_id: str
    views_last_7d: int
    price_changes_last_30d: int
    click_events_last_7d: int


def classify_priority(signal: ProductActivitySignal) -> Priority:
    if signal.views_last_7d >= 500 or signal.price_changes_last_30d >= 5:
        return Priority.HIGH
    if signal.views_last_7d >= 50 or signal.price_changes_last_30d >= 1:
        return Priority.MEDIUM
    return Priority.LOW


def next_crawl_at(priority: Priority, last_crawled_at: datetime | None = None) -> datetime:
    base = last_crawled_at or datetime.now(timezone.utc)
    return base + _REFRESH_INTERVAL[priority]
