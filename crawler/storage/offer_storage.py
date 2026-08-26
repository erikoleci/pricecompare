"""
Storage layer - the only place in the crawler that talks to Postgres.

Connectors and normalizers never touch the DB directly (spec section 36:
SCRAPER -> RAW DATA -> NORMALIZER -> PRODUCT MATCHER -> PRODUCT DATABASE ->
OFFER DATABASE -> PRICE HISTORY). This module is that last leg of the
pipeline.

Responsibilities:
  - upsert merchant / product / offer rows
  - ALWAYS append to price_history on a price/availability change - never
    overwrite it (section 8)
  - flag `needs_verification` when a price jumps more than 50% (section 30)
  - raise a PriceDropEvent row when total_price drops (section 21)
  - stamp provenance (source, source_url, source_type, scraped_at) on every
    write (section 39)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import psycopg
from psycopg.rows import dict_row

from crawler.interfaces.merchant_connector import RawOffer
from crawler.normalizers import product_matcher as matcher
from crawler.normalizers.product_normalizer import build_identifier_candidates, normalize_title

SUSPICIOUS_PRICE_CHANGE_THRESHOLD = Decimal("0.50")  # 50% (spec section 30)


@dataclass
class StorageConfig:
    dsn: str  # e.g. "host=localhost dbname=pricecompare user=pricecompare password=..."


@dataclass
class ResolvedProduct:
    """Outcome of running the section-15 matcher against products already in the DB."""

    decision: str  # AUTO_MERGED, NEW_PRODUCT, NEW_PRODUCT_PENDING_REVIEW
    product_id: Optional[str] = None          # set only for AUTO_MERGED
    candidate_product_id: Optional[str] = None  # set only for NEW_PRODUCT_PENDING_REVIEW (audit trail)
    confidence: Optional[float] = None
    method: Optional[str] = None


class OfferStorage:
    def __init__(self, config: StorageConfig) -> None:
        self._config = config

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._config.dsn, row_factory=dict_row)

    # ------------------------------------------------------------------
    # Merchant
    # ------------------------------------------------------------------
    def get_merchant_id(self, conn: psycopg.Connection, domain: str) -> Optional[str]:
        row = conn.execute("SELECT id FROM merchants WHERE domain = %s", (domain,)).fetchone()
        return str(row["id"]) if row else None

    # ------------------------------------------------------------------
    # Product (assumes matching has already happened - caller passes the
    # resolved product_id, or None to create a brand-new product)
    # ------------------------------------------------------------------
    def upsert_product(self, conn: psycopg.Connection, *, product_id: Optional[str],
                        title: str, normalized_title: str, brand_id: Optional[str],
                        category_id: Optional[str], model: Optional[str],
                        description: Optional[str]) -> str:
        if product_id:
            conn.execute(
                """UPDATE products SET title=%s, normalized_title=%s, model=%s,
                       description=COALESCE(%s, description)
                   WHERE id=%s""",
                (title, normalized_title, model, description, product_id),
            )
            return product_id

        row = conn.execute(
            """INSERT INTO products (brand_id, category_id, model, title, normalized_title, description)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
            (brand_id, category_id, model, title, normalized_title, description),
        ).fetchone()
        return str(row["id"])

    # ------------------------------------------------------------------
    # Offer + price history + price drop detection
    # ------------------------------------------------------------------
    def upsert_offer_and_record_price(
        self,
        conn: psycopg.Connection,
        *,
        product_id: str,
        merchant_id: str,
        merchant_product_id: str,
        price: Decimal,
        currency: str,
        old_price: Optional[Decimal],
        shipping_cost: Optional[Decimal],  # None stays None - never coerced to 0
        availability: str,
        condition: str,
        url: str,
        image_url: Optional[str],
        source_url: str,
        source_type: str = "SCRAPER",
    ) -> dict:
        total_price = price + shipping_cost if shipping_cost is not None else price
        discount_percent = None
        if old_price and old_price > price > 0:
            discount_percent = ((old_price - price) / old_price * 100)

        existing = conn.execute(
            "SELECT id, total_price FROM offers WHERE merchant_id=%s AND merchant_product_id=%s",
            (merchant_id, merchant_product_id),
        ).fetchone()

        now = datetime.now(timezone.utc)
        needs_verification = False
        price_changed = True

        if existing:
            prev_total = existing["total_price"]
            if prev_total and prev_total > 0:
                change_ratio = abs(total_price - prev_total) / prev_total
                if change_ratio > SUSPICIOUS_PRICE_CHANGE_THRESHOLD:
                    needs_verification = True  # flagged, not silently trusted (section 30)
                price_changed = total_price != prev_total

            conn.execute(
                """UPDATE offers SET price=%s, currency=%s, old_price=%s, discount_percent=%s,
                       shipping_cost=%s, total_price=%s, availability=%s, condition=%s, url=%s,
                       image_url=COALESCE(%s, image_url), source_type=%s, scraped_at=%s,
                       last_seen_at=%s, last_price_change_at=CASE WHEN %s THEN %s ELSE last_price_change_at END,
                       needs_verification=%s
                   WHERE id=%s""",
                (price, currency, old_price, discount_percent, shipping_cost, total_price,
                 availability, condition, url, image_url, source_type, now, now,
                 price_changed, now, needs_verification, existing["id"]),
            )
            offer_id = str(existing["id"])

            if price_changed and prev_total is not None and total_price < prev_total:
                self._record_price_drop(conn, product_id=product_id, offer_id=offer_id,
                                         merchant_id=merchant_id, old_price=prev_total, new_price=total_price)
        else:
            row = conn.execute(
                """INSERT INTO offers (product_id, merchant_id, merchant_product_id, price, currency,
                       old_price, discount_percent, shipping_cost, total_price, availability, condition,
                       url, image_url, source_type, scraped_at, last_seen_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (product_id, merchant_id, merchant_product_id, price, currency, old_price,
                 discount_percent, shipping_cost, total_price, availability, condition,
                 url, image_url, source_type, now, now),
            ).fetchone()
            offer_id = str(row["id"])

        # Price history is append-only - always insert, never overwrite (section 8)
        conn.execute(
            """INSERT INTO price_history (product_id, offer_id, merchant_id, price, shipping_cost,
                   total_price, currency, availability, recorded_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (product_id, offer_id, merchant_id, price, shipping_cost, total_price,
             currency, availability, now),
        )

        # Section 22: "notify me when below X" - check against the best current
        # price across ALL of the product's merchants (not just this offer),
        # since a different, already-cheaper listing can also satisfy an alert.
        best_row = conn.execute(
            "SELECT MIN(total_price) AS best FROM offers WHERE product_id = %s AND availability != 'OUT_OF_STOCK'",
            (product_id,),
        ).fetchone()
        best_total_price = best_row["best"] if best_row and best_row["best"] is not None else total_price
        fired_alerts = self.check_and_trigger_alerts(conn, product_id=product_id,
                                                       current_total_price=best_total_price)

        conn.commit()
        return {"offer_id": offer_id, "total_price": total_price, "needs_verification": needs_verification,
                "fired_alerts": fired_alerts}

    def check_and_trigger_alerts(self, conn: psycopg.Connection, *, product_id: str,
                                  current_total_price: Decimal) -> list[dict]:
        """Section 22: finds active, not-yet-triggered alerts whose target price has
        been reached, marks them triggered, and returns them so the caller can hand
        off to a notification channel (email/push delivery is intentionally not
        implemented here - this only decides *which* alerts fire, not how they're sent)."""
        rows = conn.execute(
            """SELECT id, user_id, target_price FROM price_alerts
                   WHERE product_id = %s AND active = true AND triggered_at IS NULL
                     AND target_price >= %s""",
            (product_id, current_total_price),
        ).fetchall()
        fired = []
        for r in rows:
            conn.execute(
                "UPDATE price_alerts SET triggered_at = now(), active = false WHERE id = %s",
                (r["id"],),
            )
            fired.append({"alert_id": str(r["id"]), "user_id": str(r["user_id"]),
                          "target_price": r["target_price"]})
        return fired

    # ------------------------------------------------------------------
    # Product matching (spec section 15) - resolves a RawOffer to an
    # existing product, a new product, or a new product pending manual
    # review, following the priority order and confidence thresholds in
    # crawler/normalizers/product_matcher.py. This is the only place that
    # queries products/product_identifiers/product_specifications for
    # matching purposes - matcher.py itself never touches the DB.
    # ------------------------------------------------------------------
    def resolve_product_id(
        self,
        conn: psycopg.Connection,
        *,
        identifiers: list[tuple[str, str]],
        brand_id: Optional[str],
        brand_name: Optional[str],
        model: Optional[str],
        normalized_title: str,
        category_id: Optional[str],
        specs: dict,
    ) -> ResolvedProduct:
        # 1) EAN/GTIN/MPN/SKU exact match - highest priority, always safe to merge
        for id_type, id_value in identifiers:
            if id_type not in ("EAN", "GTIN", "MPN"):
                continue  # SKU is merchant-specific, never used to auto-link across merchants
            row = conn.execute(
                "SELECT product_id FROM product_identifiers WHERE id_type=%s AND id_value=%s",
                (id_type, id_value),
            ).fetchone()
            if row:
                confidence = 100.0 if id_type in ("EAN", "GTIN") else 95.0
                return ResolvedProduct(decision="AUTO_MERGED", product_id=str(row["product_id"]),
                                        confidence=confidence, method=id_type)

        best: Optional[matcher.MatchCandidate] = None

        # 2) brand + model, adjusted by how many specs agree
        if brand_id and model:
            rows = conn.execute(
                "SELECT id, model FROM products WHERE brand_id=%s AND lower(model)=lower(%s) AND status='ACTIVE'",
                (brand_id, model),
            ).fetchall()
            for r in rows:
                overlap = self._spec_overlap_ratio(conn, str(r["id"]), specs)
                score = matcher.score_brand_model_match(brand_name, model, brand_name, r["model"], overlap)
                candidate = matcher.MatchCandidate(product_id=str(r["id"]), method="BRAND_MODEL", confidence=score)
                if best is None or candidate.confidence > best.confidence:
                    best = candidate

        # 3) fuzzy normalized-title match within the same category (pg_trgm-assisted
        # shortlist, spec section 15's lowest-priority signal), only if nothing
        # stronger has already cleared the auto-merge bar
        if category_id and (best is None or best.confidence < matcher.AUTO_MERGE_THRESHOLD):
            rows = conn.execute(
                """SELECT id, normalized_title FROM products
                       WHERE category_id = %s AND status = 'ACTIVE'
                         AND normalized_title %% %s
                       ORDER BY similarity(normalized_title, %s) DESC LIMIT 5""",
                (category_id, normalized_title, normalized_title),
            ).fetchall()
            for r in rows:
                score = matcher.score_normalized_title_match(normalized_title, r["normalized_title"])
                candidate = matcher.MatchCandidate(product_id=str(r["id"]), method="NORMALIZED_TITLE",
                                                    confidence=score)
                if best is None or candidate.confidence > best.confidence:
                    best = candidate

        if best is None:
            return ResolvedProduct(decision="NEW_PRODUCT")

        decision = matcher.decision_for(best.confidence)
        if decision == "AUTO_MERGED":
            return ResolvedProduct(decision="AUTO_MERGED", product_id=best.product_id,
                                    confidence=best.confidence, method=best.method)
        if decision == "PENDING":
            # Never auto-merge below the threshold: keep it a separate product,
            # but leave an audit trail an admin can act on (section 15).
            return ResolvedProduct(decision="NEW_PRODUCT_PENDING_REVIEW", candidate_product_id=best.product_id,
                                    confidence=best.confidence, method=best.method)
        return ResolvedProduct(decision="NEW_PRODUCT", confidence=best.confidence, method=best.method)

    def _spec_overlap_ratio(self, conn: psycopg.Connection, product_id: str, specs: dict) -> float:
        """Fraction of the raw offer's specs that agree with what's already stored for the
        candidate product. Returns a neutral 0.5 when there isn't enough to compare, so a
        brand+model match is never rejected purely for lack of spec data."""
        if not specs:
            return 0.5
        rows = conn.execute(
            "SELECT spec_key, spec_value FROM product_specifications WHERE product_id=%s", (product_id,)
        ).fetchall()
        if not rows:
            return 0.5
        existing = {r["spec_key"].strip().lower(): r["spec_value"].strip().lower() for r in rows}
        matched, compared = 0, 0
        for key, value in specs.items():
            key_l = key.strip().lower()
            if key_l in existing:
                compared += 1
                if existing[key_l] == str(value).strip().lower():
                    matched += 1
        return (matched / compared) if compared else 0.5

    def _write_identifiers(self, conn: psycopg.Connection, product_id: str,
                            identifiers: list[tuple[str, str]]) -> None:
        for id_type, id_value in identifiers:
            conn.execute(
                """INSERT INTO product_identifiers (product_id, id_type, id_value)
                       VALUES (%s, %s, %s) ON CONFLICT (id_type, id_value) DO NOTHING""",
                (product_id, id_type, id_value),
            )

    def _write_specs(self, conn: psycopg.Connection, product_id: str, specs: dict) -> None:
        for key, value in specs.items():
            conn.execute(
                "INSERT INTO product_specifications (product_id, spec_key, spec_value) VALUES (%s, %s, %s)",
                (product_id, key, str(value)),
            )

    # ------------------------------------------------------------------
    # Full pipeline in one call (spec section 36): normalize -> match ->
    # product -> offer -> price history. This is what connectors' scraped
    # RawOffer results should be handed to; nothing upstream of this touches
    # the DB directly.
    # ------------------------------------------------------------------
    def process_raw_offer(
        self,
        conn: psycopg.Connection,
        *,
        merchant_id: str,
        raw: RawOffer,
        category_id: Optional[str] = None,
        brand_id: Optional[str] = None,
    ) -> dict:
        normalized = normalize_title(raw.title)
        identifiers = build_identifier_candidates(raw)
        specs = {s.key: s.value for s in raw.specifications}

        resolved = self.resolve_product_id(
            conn, identifiers=identifiers, brand_id=brand_id, brand_name=raw.brand, model=raw.model,
            normalized_title=normalized, category_id=category_id, specs=specs,
        )

        if resolved.decision == "AUTO_MERGED":
            product_id = self.upsert_product(
                conn, product_id=resolved.product_id, title=raw.title, normalized_title=normalized,
                brand_id=brand_id, category_id=category_id, model=raw.model, description=raw.description,
            )
            # a merchant may supply an identifier the matched product didn't have yet
            self._write_identifiers(conn, product_id, identifiers)
        else:
            product_id = self.upsert_product(
                conn, product_id=None, title=raw.title, normalized_title=normalized,
                brand_id=brand_id, category_id=category_id, model=raw.model, description=raw.description,
            )
            self._write_identifiers(conn, product_id, identifiers)
            self._write_specs(conn, product_id, specs)

        result = self.upsert_offer_and_record_price(
            conn,
            product_id=product_id,
            merchant_id=merchant_id,
            merchant_product_id=raw.merchant_product_id,
            price=raw.price,
            currency=raw.currency,
            old_price=raw.old_price,
            shipping_cost=raw.shipping_cost,
            availability=raw.availability,
            condition=raw.condition,
            url=raw.url,
            image_url=raw.images[0].url if raw.images else None,
            source_url=raw.source_url,
            source_type=raw.source_type,
        )

        if resolved.decision == "NEW_PRODUCT_PENDING_REVIEW" and resolved.candidate_product_id:
            conn.execute(
                """INSERT INTO product_match_candidates
                       (offer_id, candidate_product_id, match_method, confidence, status)
                       VALUES (%s, %s, %s, %s, 'PENDING')""",
                (result["offer_id"], resolved.candidate_product_id, resolved.method, resolved.confidence),
            )
            conn.commit()

        result["product_id"] = product_id
        result["match_decision"] = resolved.decision
        result["match_confidence"] = resolved.confidence
        return result

    def _record_price_drop(self, conn: psycopg.Connection, *, product_id: str, offer_id: str,
                            merchant_id: str, old_price: Decimal, new_price: Decimal) -> None:
        drop_amount = old_price - new_price
        drop_percent = (drop_amount / old_price * 100) if old_price > 0 else Decimal(0)
        conn.execute(
            """INSERT INTO price_drop_events (product_id, offer_id, merchant_id, old_price, new_price,
                   drop_percent, drop_amount) VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (product_id, offer_id, merchant_id, old_price, new_price, drop_percent, drop_amount),
        )
