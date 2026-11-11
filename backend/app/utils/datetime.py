"""Datetime helpers shared by collectors."""

from __future__ import annotations

from datetime import UTC, datetime


def parse_iso_datetime(value: str | None) -> datetime | None:
    """Parse ISO-8601 including `Z` and `+0300` forms; return timezone-aware UTC."""
    if not value:
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def from_unix_timestamp(value: int | float | str | None) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(float(value), tz=UTC)
    except (ValueError, TypeError, OSError):
        return None
