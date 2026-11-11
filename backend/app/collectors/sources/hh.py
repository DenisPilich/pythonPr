"""hh.ru API adapter.

The list endpoint does not return a full description, only a two-part snippet
(requirement + responsibility). That snippet is what the normalizer receives:
fetching `/vacancies/{id}` for every item would cost one request per vacancy at a
10 req/min budget. Detail fetching is a documented future improvement with its own
rate budget.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.collectors.base import BaseCollector
from app.collectors.errors import SourceResponseError
from app.domain.dto import CollectedVacancy, SalaryInput
from app.domain.enums import SalaryPeriod, WorkFormat
from app.ports.vacancy_source import CollectorContext, CollectorPage
from app.utils.datetime import parse_iso_datetime


_CURRENCIES = {
    "RUR": "RUB",
    "RUB": "RUB",
    "USD": "USD",
    "EUR": "EUR",
    "KZT": "KZT",
    "BYR": "BYN",
    "UAH": "UAH",
    "GEL": "GEL",
    "AZN": "AZN",
    "UZS": "UZS",
    "KGS": "KGS",
}


def _as_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class HhCollector(BaseCollector):
    code = "hh"

    async def fetch_page(self, page: int, ctx: CollectorContext) -> CollectorPage:
        terms = self._config.get("text") or ["python"]
        if isinstance(terms, str):
            terms = [terms]
        params: dict[str, Any] = {
            "text": " OR ".join(str(term) for term in terms),
            "per_page": int(self._config.get("per_page", 20)),
            "page": page,
            "order_by": "publication_time",
        }
        area = self._config.get("area")
        if area:
            params["area"] = area

        payload = await self._http.get_json(f"{self._base_url()}/vacancies", params=params)
        if not isinstance(payload, dict) or "items" not in payload:
            raise SourceResponseError("hh: response has no `items` field")

        items = payload.get("items") or []
        pages = _as_int(payload.get("pages")) or 0
        return CollectorPage(
            items=items,
            has_next=(page + 1 < pages) and (page + 1 < ctx.max_pages),
        )

    def map_item(self, item: Mapping[str, Any]) -> CollectedVacancy | None:
        external_id = item.get("id")
        title = str(item.get("name") or "").strip()
        if external_id is None or not title:
            return None

        employer = item.get("employer") or {}
        area = item.get("area") or {}
        snippet = item.get("snippet") or {}
        description = "\n\n".join(
            part.strip()
            for part in (snippet.get("requirement"), snippet.get("responsibility"))
            if isinstance(part, str) and part.strip()
        )

        schedule_id = (item.get("schedule") or {}).get("id")
        return CollectedVacancy(
            source_code=self.code,
            external_id=str(external_id),
            url=str(item.get("alternate_url") or f"https://hh.ru/vacancy/{external_id}"),
            title=title,
            company_name=str(employer.get("name") or "Unknown"),
            description=description,
            published_at=parse_iso_datetime(item.get("published_at")),
            location_raw=str(area.get("name")) if area.get("name") else None,
            work_format_hint=WorkFormat.REMOTE if schedule_id == "remote" else None,
            salary=self._map_salary(item.get("salary")),
            employment_type=(item.get("employment") or {}).get("id"),
            raw_payload=dict(item),
        )

    @staticmethod
    def _map_salary(raw: Any) -> SalaryInput | None:
        if not isinstance(raw, dict):
            return None
        low = _as_int(raw.get("from"))
        high = _as_int(raw.get("to"))
        if low is None and high is None:
            return None
        currency = _CURRENCIES.get(str(raw.get("currency") or "").upper())
        return SalaryInput(
            min=low,
            max=high,
            currency=currency,
            period=SalaryPeriod.MONTH,
            is_estimated=low is None or high is None,
        )
