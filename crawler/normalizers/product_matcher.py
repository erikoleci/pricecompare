"""
Decides whether a newly scraped RawOffer belongs to an existing Product or
needs a new one / manual review. Mirrors spec section 15's priority order
and confidence thresholds. This module only computes a confidence score -
it never writes to the DB and never auto-merges below the threshold itself;
the caller (storage layer) is responsible for enforcing:

    confidence >= 90  -> safe to auto-link
    70 <= confidence < 90 -> store as product_match_candidates, status=PENDING
    confidence < 70   -> status=MANUAL_REVIEW, never auto-merged
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Optional

AUTO_MERGE_THRESHOLD = 90
POSSIBLE_MATCH_THRESHOLD = 70


@dataclass
class MatchCandidate:
    product_id: str
    method: str
    confidence: float


def score_identifier_match(raw_id_type: str, raw_id_value: str,
                            existing_id_type: str, existing_id_value: str) -> Optional[float]:
    if raw_id_value != existing_id_value:
        return None
    if raw_id_type == "EAN" and existing_id_type == "EAN":
        return 100.0
    if raw_id_type == "GTIN" and existing_id_type == "GTIN":
        return 100.0
    if raw_id_type == "MPN" and existing_id_type == "MPN":
        return 95.0
    return None


def score_brand_model_match(raw_brand: Optional[str], raw_model: Optional[str],
                             existing_brand: Optional[str], existing_model: Optional[str],
                             spec_overlap_ratio: float) -> float:
    """spec_overlap_ratio in [0,1]: fraction of key specs (storage/color/ram/...) that agree."""
    if not raw_brand or not raw_model or not existing_brand or not existing_model:
        return 0.0
    if raw_brand.strip().lower() != existing_brand.strip().lower():
        return 0.0
    if raw_model.strip().lower() != existing_model.strip().lower():
        return 0.0
    # brand + model match = base 90, adjusted down if specs disagree
    return max(70.0, 90.0 * (0.5 + 0.5 * spec_overlap_ratio))


def score_normalized_title_match(normalized_a: str, normalized_b: str) -> float:
    ratio = SequenceMatcher(None, normalized_a, normalized_b).ratio()
    # A high textual similarity alone should never exceed the "possible match"
    # band - titles are the weakest signal (spec section 15 places it near the bottom).
    return round(ratio * POSSIBLE_MATCH_THRESHOLD, 2)


def best_match(candidates: list[MatchCandidate]) -> Optional[MatchCandidate]:
    if not candidates:
        return None
    return max(candidates, key=lambda c: c.confidence)


def decision_for(confidence: float) -> str:
    if confidence >= AUTO_MERGE_THRESHOLD:
        return "AUTO_MERGED"
    if confidence >= POSSIBLE_MATCH_THRESHOLD:
        return "PENDING"  # queued for manual review, not auto-merged
    return "REJECTED"
