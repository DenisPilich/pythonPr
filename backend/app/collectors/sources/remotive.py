"""Remotive adapter (`/api/remote-jobs`, single payload with a `jobs` array)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.collectors.base import BaseCollector
from app.collectors.errors import SourceResponseError
from app.domain.dto import CollectedVacancy
from app.domain.enums import WorkFormat
from app.ports.vacancy_source import CollectorContext, CollectorPage
from app.utils.datetime import parse_iso_datetime


class RemotiveCollector(BaseCollector):
    code = "remotive"

    async def fetch_page(self, page: int, ctx: CollectorContext) -> CollectorPage:
        if page > 0:
            return CollectorPage(items=(), has_next=False)

        limit = int(self._config.get("limit", 100))
        payload = await self._http.get_json(self._base_url(), params={"limit": limit})
        if not isinstance(payload, dict) or "jobs" not in payload:
            raise SourceResponseError("remotive: response has no `jobs` field")
        jobs = [job for job in payload["jobs"] if isinstance(job, dict)]
        return CollectorPage(items=jobs[:limit], has_next=False)

    def map_item(self, item: Mapping[str, Any]) -> CollectedVacancy | None:
        external_id = item.get("id")
        title = str(item.get("title") or "").strip()
        company = str(item.get("company_name") or "").strip()
        url = item.get("url")
        if not external_id or not title or not company or not url:
            return None

        return CollectedVacancy(
            source_code=self.code,
            external_id=str(external_id),
            url=str(url),
            title=title,
            company_name=company,
            description=str(item.get("description") or ""),
            published_at=parse_iso_datetime(item.get("publication_date")),
            location_raw=str(item.get("candidate_required_location") or "Remote"),
            work_format_hint=WorkFormat.REMOTE,
            salary_text=str(item.get("salary") or "") or None,
            employment_type=str(item.get("job_type") or "") or None,
            raw_payload=dict(item),
        )
