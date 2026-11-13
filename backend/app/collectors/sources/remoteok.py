"""RemoteOK adapter.

`https://remoteok.com/api` returns one large array whose first element is a legal
notice, not a vacancy. Salaries are USD per year. RemoteOK asks for attribution
and a link back to the original posting — both are preserved (`url` is the
original job page and the Telegram message links to it).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.collectors.base import BaseCollector
from app.collectors.errors import SourceResponseError
from app.domain.dto import CollectedVacancy, SalaryInput
from app.domain.enums import SalaryPeriod, WorkFormat
from app.ports.vacancy_source import CollectorContext, CollectorPage
from app.utils.datetime import from_unix_timestamp, parse_iso_datetime


def _as_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


# RemoteOK is a general remote-job board, not a developer-only board. Its feed
# also carries clinical, sales and support roles, which are useless for a
# developer radar. Keep the filter conservative: title first, tags second.
_NON_DEV_TITLE = (
    "clinical",
    "patient",
    "nurse",
    "medical",
    "sales",
    "marketing",
    "coach",
    "recruit",
    "accountant",
    "customer",
    "travel support",
    "tutor",
    "teacher",
    "writer",
    "editor",
    "designer",
    "product manager",
    "project manager",
    "data entry",
    "operations manager",
    "supply chain",
    "education",
    "curriculum",
    "school",
)
_DEV_TITLE = (
    "developer",
    "engineer",
    "programmer",
    "software",
    "backend",
    "back-end",
    "frontend",
    "front-end",
    "full stack",
    "fullstack",
    "devops",
    "site reliability",
    "sre",
    "data scientist",
    "machine learning",
    "ml engineer",
    "ai engineer",
    "qa ",
    "automation",
    "architect",
    "python",
    "javascript",
    "typescript",
    "react",
    "node",
    "golang",
    "rust",
    "java",
    "php",
    "ruby",
    "c++",
    "c#",
    "sql",
    "cloud",
    "platform",
    "security",
)
_DEV_TAGS = frozenset(
    {
        "python",
        "javascript",
        "typescript",
        "react",
        "node",
        "golang",
        "rust",
        "java",
        "php",
        "ruby",
        "sql",
        "aws",
        "docker",
        "kubernetes",
        "devops",
        "backend",
        "frontend",
        "fullstack",
        "web3",
        "solidity",
        "ml",
        "ai",
        "machine-learning",
        "data-science",
        "engineering",
        "software",
    }
)


def is_relevant_remoteok(item: Mapping[str, Any]) -> bool:
    """Whether a RemoteOK row is a developer/engineering role."""
    title = str(item.get("position") or item.get("title") or "").lower()
    if any(marker in title for marker in _NON_DEV_TITLE):
        return False
    if any(marker in title for marker in _DEV_TITLE):
        return True
    tags = {str(tag).lower() for tag in item.get("tags") or ()}
    return bool(tags & _DEV_TAGS)


class RemoteOkCollector(BaseCollector):
    code = "remoteok"

    async def fetch_page(self, page: int, ctx: CollectorContext) -> CollectorPage:
        if page > 0:
            return CollectorPage(items=(), has_next=False)

        payload = await self._http.get_json(self._base_url())
        if not isinstance(payload, list):
            raise SourceResponseError("remoteok: expected a JSON array")

        items = [
            item
            for item in payload
            if isinstance(item, dict)
            and "legal" not in item
            and item.get("id")
            and is_relevant_remoteok(item)
        ]
        limit = int(self._config.get("max_items", 200))
        return CollectorPage(items=items[:limit], has_next=False)

    def map_item(self, item: Mapping[str, Any]) -> CollectedVacancy | None:
        external_id = item.get("id")
        title = str(item.get("position") or item.get("title") or "").strip()
        company = str(item.get("company") or "").strip()
        if not external_id or not title or not company:
            return None

        slug = item.get("slug")
        url = item.get("url") or (f"https://remoteok.com/remote-jobs/{slug}" if slug else None)
        if not url:
            return None

        salary_min = _as_int(item.get("salary_min"))
        salary_max = _as_int(item.get("salary_max"))
        salary = (
            SalaryInput(
                min=salary_min,
                max=salary_max,
                currency="USD",
                period=SalaryPeriod.YEAR,
                is_estimated=salary_min is None or salary_max is None,
            )
            if salary_min or salary_max
            else None
        )

        return CollectedVacancy(
            source_code=self.code,
            external_id=str(external_id),
            url=str(url),
            title=title,
            company_name=company,
            description=str(item.get("description") or ""),
            published_at=parse_iso_datetime(item.get("date"))
            or from_unix_timestamp(item.get("epoch")),
            location_raw=str(item.get("location") or "Remote"),
            work_format_hint=WorkFormat.REMOTE,
            salary=salary,
            employment_type=None,
            raw_payload=dict(item),
        )
