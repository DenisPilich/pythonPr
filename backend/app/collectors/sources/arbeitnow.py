"""Arbeitnow job-board API adapter (paginated, `data` + `links.next`)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.collectors.base import BaseCollector
from app.collectors.errors import SourceResponseError
from app.domain.dto import CollectedVacancy
from app.domain.enums import WorkFormat
from app.ports.vacancy_source import CollectorContext, CollectorPage
from app.utils.datetime import from_unix_timestamp


class ArbeitnowCollector(BaseCollector):
    code = "arbeitnow"

    async def fetch_page(self, page: int, ctx: CollectorContext) -> CollectorPage:
        payload = await self._http.get_json(self._base_url(), params={"page": page + 1})
        if not isinstance(payload, dict) or "data" not in payload:
            raise SourceResponseError("arbeitnow: response has no `data` field")
        items = [item for item in payload["data"] if isinstance(item, dict)]
        has_next = bool((payload.get("links") or {}).get("next"))
        return CollectorPage(items=items, has_next=has_next)

    def map_item(self, item: Mapping[str, Any]) -> CollectedVacancy | None:
        external_id = item.get("slug")
        title = str(item.get("title") or "").strip()
        company = str(item.get("company_name") or "").strip()
        url = item.get("url")
        if not external_id or not title or not company or not url:
            return None

        job_types = item.get("job_types") or []
        employment_type = str(job_types[0]) if isinstance(job_types, list) and job_types else None
        remote = item.get("remote")

        return CollectedVacancy(
            source_code=self.code,
            external_id=str(external_id),
            url=str(url),
            title=title,
            company_name=company,
            description=str(item.get("description") or ""),
            published_at=from_unix_timestamp(item.get("created_at")),
            location_raw=str(item.get("location") or "") or None,
            work_format_hint=WorkFormat.REMOTE if remote is True else None,
            employment_type=employment_type,
            raw_payload=dict(item),
        )
