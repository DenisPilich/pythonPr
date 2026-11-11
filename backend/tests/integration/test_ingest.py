from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.dto import CollectedVacancy
from app.domain.enums import SourceKind
from app.models import Company, Source, Vacancy, VacancySource, VacancyTechnology
from app.normalization.pipeline import NormalizationPipeline
from app.services.ingest import IngestService


pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("taxonomy_rows")]

PIPELINE = NormalizationPipeline()


def collected(**overrides: Any) -> CollectedVacancy:
    values: dict[str, Any] = {
        "source_code": "hh",
        "external_id": "1",
        "url": "https://hh.ru/vacancy/1",
        "title": "Senior Python Developer",
        "company_name": "Acme, Inc.",
        "description": "<p>Python, FastAPI, PostgreSQL, Docker</p>",
        "location_raw": "Remote",
    }
    values.update(overrides)
    return CollectedVacancy(**values)


async def make_source(session: AsyncSession, code: str = "hh") -> Source:
    source = Source(
        code=code,
        name=code,
        kind=SourceKind.JSON_API,
        base_url="https://example.com",
        rate_limit_per_min=10_000,
    )
    session.add(source)
    await session.flush()
    return source


async def test_ingest_creates_then_deduplicates(db_session: AsyncSession) -> None:
    source = await make_source(db_session)
    service = IngestService(db_session)

    first = await service.ingest(PIPELINE.normalize(collected()), source.id)
    second = await service.ingest(
        PIPELINE.normalize(collected(external_id="1", url="https://hh.ru/vacancy/1")),
        source.id,
    )

    assert first.status == "created"
    assert second.status == "duplicate"
    assert first.technologies >= 4
    assert await db_session.scalar(select(func.count()).select_from(Vacancy)) == 1
    assert await db_session.scalar(select(func.count()).select_from(VacancySource)) == 1


async def test_cross_source_syndication_is_one_vacancy(db_session: AsyncSession) -> None:
    hh = await make_source(db_session, "hh")
    remoteok = await make_source(db_session, "remoteok")
    service = IngestService(db_session)

    await service.ingest(PIPELINE.normalize(collected()), hh.id)
    outcome = await service.ingest(
        PIPELINE.normalize(
            collected(
                source_code="remoteok",
                external_id="remote-111",
                url="https://remoteok.com/remote-jobs/111",
            )
        ),
        remoteok.id,
    )

    assert outcome.status == "duplicate"
    assert await db_session.scalar(select(func.count()).select_from(Vacancy)) == 1
    assert await db_session.scalar(select(func.count()).select_from(VacancySource)) == 2


async def test_richer_description_updates_vacancy(db_session: AsyncSession) -> None:
    source = await make_source(db_session)
    service = IngestService(db_session)

    await service.ingest(PIPELINE.normalize(collected(description="<p>Python</p>")), source.id)
    outcome = await service.ingest(
        PIPELINE.normalize(
            collected(description="<p>Python, FastAPI, PostgreSQL, Docker, Kubernetes</p>")
        ),
        source.id,
    )

    assert outcome.status == "updated"
    vacancy = await db_session.scalar(select(Vacancy))
    assert vacancy is not None
    assert "Kubernetes" in vacancy.description_clean
    technology_count = await db_session.scalar(select(func.count()).select_from(VacancyTechnology))
    assert technology_count is not None and technology_count >= 5


async def test_company_names_are_canonicalized(db_session: AsyncSession) -> None:
    source = await make_source(db_session)
    service = IngestService(db_session)

    await service.ingest(
        PIPELINE.normalize(collected(company_name="Acme, Inc.", title="Backend Engineer")),
        source.id,
    )
    await service.ingest(
        PIPELINE.normalize(
            collected(
                company_name="ACME LLC",
                title="Data Engineer",
                external_id="2",
                url="https://hh.ru/vacancy/2",
            )
        ),
        source.id,
    )

    assert await db_session.scalar(select(func.count()).select_from(Company)) == 1


async def test_salary_and_classification_are_persisted(db_session: AsyncSession) -> None:
    source = await make_source(db_session)
    service = IngestService(db_session)

    await service.ingest(PIPELINE.normalize(collected(salary_text="€1.2k–1.8k / month")), source.id)

    vacancy = await db_session.scalar(select(Vacancy))
    assert vacancy is not None
    assert vacancy.salary_min == 1200
    assert vacancy.salary_max == 1800
    assert vacancy.salary_currency == "EUR"
    assert vacancy.salary_monthly_eur is not None
    assert vacancy.work_format.value == "remote"
    assert vacancy.seniority.value == "senior"
    assert vacancy.language.value == "en"
