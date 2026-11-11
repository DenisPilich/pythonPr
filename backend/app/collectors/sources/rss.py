"""RSS adapter for We Work Remotely.

RSS is the fallback protocol for boards without a JSON API. Titles follow
`"Company: Role"`; the description is HTML and goes through the same normalizer as
every other source. `published_parsed` is converted from `time.struct_time`.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import feedparser

from app.collectors.base import BaseCollector
from app.collectors.errors import SourceResponseError
from app.domain.dto import CollectedVacancy
from app.domain.enums import WorkFormat
from app.ports.vacancy_source import CollectorContext, CollectorPage


class WeWorkRemotelyCollector(BaseCollector):
    code = "weworkremotely"

    async def fetch_page(self, page: int, ctx: CollectorContext) -> CollectorPage:
        if page > 0:
            return CollectorPage(items=(), has_next=False)

        raw = await self._http.get_bytes(self._base_url())
        feed = feedparser.parse(raw)
        if feed.bozo and not feed.entries:
            raise SourceResponseError(f"rss: cannot parse feed: {feed.get('bozo_exception')}")
        limit = int(self._config.get("max_items", 100))
        entries: list[Mapping[str, Any]] = list(feed.entries[:limit])
        return CollectorPage(items=entries, has_next=False)

    def map_item(self, item: Mapping[str, Any]) -> CollectedVacancy | None:
        link = item.get("link")
        raw_title = str(item.get("title") or "").strip()
        if not link or not raw_title:
            return None

        company, title = self._split_title(raw_title)
        published = item.get("published_parsed")
        published_at = (
            datetime(
                year=published[0],
                month=published[1],
                day=published[2],
                hour=published[3],
                minute=published[4],
                second=published[5],
                tzinfo=UTC,
            )
            if published
            else None
        )

        return CollectedVacancy(
            source_code=self.code,
            external_id=str(item.get("id") or hashlib.sha256(str(link).encode()).hexdigest()[:32]),
            url=str(link),
            title=title,
            company_name=company,
            description=str(item.get("summary") or item.get("description") or ""),
            published_at=published_at,
            location_raw=str(item.get("region") or "Remote"),
            work_format_hint=WorkFormat.REMOTE,
            raw_payload={
                "title": raw_title,
                "link": str(link),
                "published": str(item.get("published") or ""),
            },
        )

    @staticmethod
    def _split_title(raw_title: str) -> tuple[str, str]:
        if ":" in raw_title:
            company, title = raw_title.split(":", 1)
            company = company.strip()
            title = title.strip()
            if company and title:
                return company, title
        return "Unknown", raw_title
