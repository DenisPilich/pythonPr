"""Collector-specific failures.

These are expected, mapped conditions: the collection service records them on the
`collector_runs` row and lets Celery decide about a retry. They must not be
confused with programming errors, which are allowed to propagate as-is.
"""

from __future__ import annotations


class CollectorError(Exception):
    """Base class for source failures."""


class SourceUnavailableError(CollectorError):
    """Timeouts, 5xx, 429 exhausted after retries."""


class SourceResponseError(CollectorError):
    """The source answered, but not with the shape we expect (schema drift)."""
