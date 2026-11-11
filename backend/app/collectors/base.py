"""`BaseCollector`: the template every source adapter fills in.

Subclasses implement exactly two methods — how to fetch one page and how to map
one vendor item — while pagination, rate limiting, retry-driven failures, logging
and run statistics are handled here once.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Mapping
from typing import Any, ClassVar

import structlog

from app.collectors.http import HttpClient
from app.collectors.rate_limit import AsyncRateLimiter
from app.core.config import Settings
from app.domain.dto import CollectedVacancy
from app.ports.vacancy_source import (
    CollectorContext,
    CollectorPage,
    CollectorStats,
    SourceConfig,
)


logger = structlog.get_logger(__name__)


class BaseCollector(ABC):
    code: ClassVar[str]

    def __init__(self, http: HttpClient, settings: Settings, source: SourceConfig) -> None:
        self._http = http
        self._settings = settings
        self.source = source
        self._limiter = AsyncRateLimiter(source.rate_limit_per_min)
        self.stats = CollectorStats()

    @property
    def _config(self) -> Mapping[str, Any]:
        return self.source.config

    def _base_url(self) -> str:
        if not self.source.base_url:
            raise ValueError(f"source {self.code!r} has no base_url")
        return self.source.base_url.rstrip("/")

    @abstractmethod
    async def fetch_page(self, page: int, ctx: CollectorContext) -> CollectorPage:
        """Fetch one page of raw items. May raise `CollectorError`."""

    @abstractmethod
    def map_item(self, item: Mapping[str, Any]) -> CollectedVacancy | None:
        """Map a vendor item; return None for unusable entries (never raise)."""

    async def collect(self, ctx: CollectorContext) -> AsyncIterator[CollectedVacancy]:
        configured_pages = int(self._config.get("max_pages", ctx.max_pages))
        max_pages = max(1, min(ctx.max_pages, configured_pages))

        for page in range(max_pages):
            await self._limiter.wait()
            result = await self.fetch_page(page, ctx)
            self.stats.fetched += len(result.items)

            for item in result.items:
                try:
                    mapped = self.map_item(item)
                except Exception:
                    logger.exception("collector_map_failed", source=self.code, page=page)
                    mapped = None
                if mapped is None:
                    self.stats.skipped += 1
                    continue
                self.stats.mapped += 1
                yield mapped

            if not result.has_next:
                break
