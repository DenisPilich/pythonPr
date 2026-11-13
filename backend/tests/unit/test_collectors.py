from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from app.collectors.http import HttpClient
from app.collectors.registry import build_collector
from app.collectors.sources.arbeitnow import ArbeitnowCollector
from app.collectors.sources.hh import HhCollector
from app.collectors.sources.remoteok import RemoteOkCollector, is_relevant_remoteok
from app.collectors.sources.remotive import RemotiveCollector
from app.collectors.sources.rss import WeWorkRemotelyCollector
from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.domain.enums import SalaryPeriod, WorkFormat
from app.ports.vacancy_source import CollectorContext, SourceConfig


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def load_json(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def source(
    code: str,
    base_url: str,
    *,
    rate_limit: int = 60_000,
    config: dict[str, Any] | None = None,
) -> SourceConfig:
    return SourceConfig(
        code=code,
        base_url=base_url,
        rate_limit_per_min=rate_limit,
        config=config or {},
    )


def test_hh_maps_item(settings: Settings) -> None:
    collector = HhCollector(HttpClient(settings), settings, source("hh", "https://api.hh.ru"))
    item = load_json("hh_page.json")["items"][0]

    mapped = collector.map_item(item)

    assert mapped is not None
    assert mapped.external_id == "123"
    assert mapped.company_name == "Acme, Inc."
    assert mapped.url == "https://hh.ru/vacancy/123"
    assert mapped.salary is not None
    assert (mapped.salary.min, mapped.salary.max) == (60000, 80000)
    assert mapped.salary.currency == "EUR"
    assert mapped.salary.period is SalaryPeriod.MONTH
    assert mapped.work_format_hint is WorkFormat.REMOTE
    assert mapped.published_at is not None
    assert "Python" in mapped.description


def test_hh_skips_incomplete_items(settings: Settings) -> None:
    collector = HhCollector(HttpClient(settings), settings, source("hh", "https://api.hh.ru"))
    assert collector.map_item({"id": "456"}) is None


@respx.mock
async def test_hh_collects_with_pagination_and_counts_skips(settings: Settings) -> None:
    respx.get("https://api.hh.ru/vacancies").mock(
        return_value=httpx.Response(200, json=load_json("hh_page.json"))
    )
    http = HttpClient(settings)
    collector = HhCollector(
        http, settings, source("hh", "https://api.hh.ru", config={"max_pages": 2})
    )
    try:
        items = [item async for item in collector.collect(CollectorContext(max_pages=2))]
    finally:
        await http.aclose()

    assert len(items) == 1
    assert collector.stats.fetched == 2
    assert collector.stats.mapped == 1
    assert collector.stats.skipped == 1


@respx.mock
async def test_remoteok_skips_legal_notice_and_maps_salary(settings: Settings) -> None:
    respx.get("https://remoteok.com/api").mock(
        return_value=httpx.Response(200, json=load_json("remoteok.json"))
    )
    http = HttpClient(settings)
    collector = RemoteOkCollector(http, settings, source("remoteok", "https://remoteok.com/api"))
    try:
        items = [item async for item in collector.collect(CollectorContext())]
    finally:
        await http.aclose()

    assert len(items) == 1
    vacancy = items[0]
    assert vacancy.company_name == "Acme"
    assert vacancy.salary is not None
    assert vacancy.salary.period is SalaryPeriod.YEAR
    assert vacancy.salary.min == 120000
    assert vacancy.work_format_hint is WorkFormat.REMOTE


@pytest.mark.parametrize(
    ("position", "tags", "expected"),
    [
        ("Senior Python Engineer", [], True),
        ("Data Engineer", ["data"], True),
        ("AI Developer", ["python"], True),
        ("Patient Care Specialist", ["medical"], False),
        ("Strategy & Operations Coach", ["sales"], False),
        ("Bilingual Patient Engagement Specialist", [], False),
        ("Travel Support Specialist", [], False),
        ("Product Designer", ["design"], False),
    ],
)
def test_remoteok_keeps_only_developer_roles(
    position: str, tags: list[str], expected: bool
) -> None:
    assert is_relevant_remoteok({"position": position, "tags": tags}) is expected


@respx.mock
async def test_remotive_maps_salary_text(settings: Settings) -> None:
    respx.get("https://remotive.com/api/remote-jobs").mock(
        return_value=httpx.Response(200, json=load_json("remotive.json"))
    )
    http = HttpClient(settings)
    collector = RemotiveCollector(
        http, settings, source("remotive", "https://remotive.com/api/remote-jobs")
    )
    try:
        items = [item async for item in collector.collect(CollectorContext())]
    finally:
        await http.aclose()

    assert len(items) == 1
    assert items[0].salary_text == "€50k - €70k"
    assert items[0].employment_type == "full_time"


@respx.mock
async def test_arbeitnow_maps_remote_flag_and_timestamp(settings: Settings) -> None:
    respx.get("https://www.arbeitnow.com/api/job-board-api").mock(
        return_value=httpx.Response(200, json=load_json("arbeitnow.json"))
    )
    http = HttpClient(settings)
    collector = ArbeitnowCollector(
        http,
        settings,
        source("arbeitnow", "https://www.arbeitnow.com/api/job-board-api"),
    )
    try:
        items = [item async for item in collector.collect(CollectorContext())]
    finally:
        await http.aclose()

    assert len(items) == 1
    vacancy = items[0]
    assert vacancy.work_format_hint is WorkFormat.REMOTE
    assert vacancy.published_at is not None
    assert vacancy.location_raw == "Berlin"


@respx.mock
async def test_rss_parses_feed_into_vacancy(settings: Settings) -> None:
    xml = (FIXTURES / "weworkremotely.xml").read_bytes()
    respx.get("https://weworkremotely.com/feed.rss").mock(
        return_value=httpx.Response(
            200, content=xml, headers={"Content-Type": "application/rss+xml"}
        )
    )
    http = HttpClient(settings)
    collector = WeWorkRemotelyCollector(
        http, settings, source("weworkremotely", "https://weworkremotely.com/feed.rss")
    )
    try:
        items = [item async for item in collector.collect(CollectorContext())]
    finally:
        await http.aclose()

    assert len(items) == 1
    vacancy = items[0]
    assert vacancy.company_name == "Delta Labs"
    assert vacancy.title == "Senior Backend Engineer"
    assert "Python" in vacancy.description
    assert vacancy.published_at is not None
    assert vacancy.work_format_hint is WorkFormat.REMOTE


def test_registry_builds_known_source(settings: Settings) -> None:
    collector = build_collector(source("hh", "https://api.hh.ru"), HttpClient(settings), settings)
    assert isinstance(collector, HhCollector)


def test_registry_rejects_unknown_source(settings: Settings) -> None:
    with pytest.raises(ConfigurationError):
        build_collector(source("unknown", "https://example.com"), HttpClient(settings), settings)
