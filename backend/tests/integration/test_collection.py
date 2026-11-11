from __future__ import annotations

from collections.abc import AsyncIterator, Mapping, Sequence
from contextlib import asynccontextmanager
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.base import BaseCollector
from app.collectors.errors import SourceUnavailableError
from app.collectors.http import HttpClient
from app.core.config import Settings
from app.domain.dto import CollectedVacancy
from app.domain.enums import CollectorRunStatus, SourceKind
from app.models import CollectorRun, Source, Vacancy
from app.normalization.pipeline import NormalizationPipeline
from app.ports.vacancy_source import CollectorContext, CollectorPage, SourceConfig
from app.services.collection import CollectionService


pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("taxonomy_rows")]

PIPELINE = NormalizationPipeline()


class StubDatabase:
    """Runs the service against the test session so the outer rollback isolates it."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        yield self._session


class FakeCollector(BaseCollector):
    code = "fake"

    def __init__(
        self,
        http: HttpClient,
        settings: Settings,
        source: SourceConfig,
        items: Sequence[CollectedVacancy | None],
        *,
        failure: Exception | None = None,
    ) -> None:
        super().__init__(http, settings, source)
        self._items = items
        self._failure = failure

    async def fetch_page(self, page: int, ctx: CollectorContext) -> CollectorPage:
        if self._failure is not None:
            raise self._failure
        items: Sequence[Mapping[str, Any]] = self._items if page == 0 else ()  # type: ignore[assignment]
        return CollectorPage(items=items, has_next=False)

    def map_item(self, item: Mapping[str, Any]) -> CollectedVacancy | None:
        return item  # type: ignore[return-value]


def collected(external_id: str = "1", title: str = "Python Developer") -> CollectedVacancy:
    return CollectedVacancy(
        source_code="fake",
        external_id=external_id,
        url=f"https://example.com/jobs/{external_id}",
        title=title,
        company_name="Acme",
        description="<p>Python and FastAPI</p>",
        location_raw="Remote",
    )


def make_collector(
    settings: Settings,
    items: Sequence[CollectedVacancy | None],
    *,
    failure: Exception | None = None,
) -> FakeCollector:
    source = SourceConfig(
        code="fake",
        base_url="https://example.com",
        rate_limit_per_min=10_000,
        config={},
    )
    return FakeCollector(HttpClient(settings), settings, source, items, failure=failure)


async def make_source(session: AsyncSession) -> Source:
    source = Source(
        code="fake",
        name="Fake",
        kind=SourceKind.JSON_API,
        base_url="https://example.com",
        rate_limit_per_min=10_000,
    )
    session.add(source)
    await session.flush()
    return source


def source_config(source: Source) -> SourceConfig:
    return SourceConfig(
        code=source.code,
        base_url=source.base_url,
        rate_limit_per_min=source.rate_limit_per_min,
        config=source.config,
    )


async def test_successful_run_records_counts(db_session: AsyncSession, settings: Settings) -> None:
    source = await make_source(db_session)
    collector = make_collector(settings, [collected("1"), collected("2", "Backend Developer")])
    service = CollectionService(StubDatabase(db_session), PIPELINE)  # type: ignore[arg-type]

    report = await service.run(source_config(source), source.id, collector, max_pages=1)

    assert report.status is CollectorRunStatus.SUCCESS
    assert (report.fetched, report.created, report.skipped) == (2, 2, 0)
    assert await db_session.scalar(select(func.count()).select_from(Vacancy)) == 2

    run = await db_session.scalar(select(CollectorRun).execution_options(populate_existing=True))
    assert run is not None
    assert run.status is CollectorRunStatus.SUCCESS
    assert run.items_created == 2
    assert run.finished_at is not None


async def test_skipped_items_make_run_partial(db_session: AsyncSession, settings: Settings) -> None:
    source = await make_source(db_session)
    collector = make_collector(settings, [collected("1"), None])
    service = CollectionService(StubDatabase(db_session), PIPELINE)  # type: ignore[arg-type]

    report = await service.run(source_config(source), source.id, collector, max_pages=1)

    assert report.status is CollectorRunStatus.PARTIAL
    assert report.skipped == 1
    assert report.created == 1


async def test_source_failure_marks_run_failed(
    db_session: AsyncSession, settings: Settings
) -> None:
    source = await make_source(db_session)
    collector = make_collector(settings, [], failure=SourceUnavailableError("boom"))
    service = CollectionService(StubDatabase(db_session), PIPELINE)  # type: ignore[arg-type]

    with pytest.raises(SourceUnavailableError):
        await service.run(source_config(source), source.id, collector, max_pages=1)

    run = await db_session.scalar(select(CollectorRun).execution_options(populate_existing=True))
    assert run is not None
    assert run.status is CollectorRunStatus.FAILED
    assert run.error is not None and "boom" in run.error
