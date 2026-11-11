"""Canonical profile representation and its hash.

The hash is the AI cache key: two profiles that differ only in list order or
letter case must produce the same analysis, otherwise every cosmetic edit would
buy a new LLM call.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from enum import StrEnum
from typing import Any


PROFILE_HASH_FIELDS: tuple[str, ...] = (
    "headline",
    "desired_positions",
    "target_seniority",
    "skills",
    "preferred_stack",
    "excluded_stack",
    "english_level",
    "min_salary_amount",
    "salary_currency",
    "preferred_locations",
    "work_formats",
    "min_match_score",
    "notifications_enabled",
    "max_notifications_per_day",
)


def _normalize_value(field: str, value: Any) -> Any:
    if isinstance(value, list):
        normalized = [
            item.value if isinstance(item, StrEnum) else str(item).strip() for item in value
        ]
        return sorted({item.casefold() for item in normalized if item})
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, str):
        return " ".join(value.split()) if field == "headline" else value.strip()
    return value


def canonical_profile(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {field: _normalize_value(field, payload.get(field)) for field in PROFILE_HASH_FIELDS}


def compute_profile_hash(payload: Mapping[str, Any]) -> str:
    canonical = canonical_profile(payload)
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
