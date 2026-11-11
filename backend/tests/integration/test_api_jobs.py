from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import (
    SalaryPeriod,
    SeniorityLevel,
    SourceKind,
    VacancyLanguage,
    WorkFormat,
)
from app.models import Company, Source, Technology, Vacancy, VacancySource, VacancyTechnology


pytestmark = pytest.mark.integration


async def _add_vacancy(
    session: AsyncSession,
    *,
    company: Company,
    source: Source,
    title: str,
    work_format: WorkFormat,
    seniority: SeniorityLevel,
    language: VacancyLanguage,
    published_at: datetime,
    salary: int | None,
    technologies: list[tuple[str, int]],
) -> Vacancy:
    technology_rows = {
        technology.slug: technology
        for technology in (await session.scalars(select(Technology))).all()
    }
    vacancy = Vacancy(
        company_id=company.id,
        title=title,
        description_clean=f"{title}. We use Python and FastAPI.",
        description_raw=f"<p>{title}</p>",
        fingerprint=hashlib.sha256(title.encode()).hexdigest(),
        content_hash=hashlib.sha256(title.encode()).hexdigest(),
        work_format=work_format,
        seniority=seniority,
        language=language,
        salary_min=salary,
        salary_max=salary,
        salary_currency="EUR" if salary else None,
        salary_period=SalaryPeriod.MONTH,
        salary_monthly_eur=salary,
        published_at=published_at,
        first_seen_at=published_at,
        last_seen_at=published_at,
    )
    session.add(vacancy)
    await session.flush()
    session.add(
        VacancySource(
            vacancy_id=vacancy.id,
            source_id=source.id,
            external_id=title,
            url=f"https://example.com/jobs/{vacancy.id}",
        )
    )
    for slug, mentions in technologies:
        session.add(
            VacancyTechnology(
                vacancy_id=vacancy.id,
                technology_id=technology_rows[slug].id,
                mentions=mentions,
            )
        )
    await session.flush()
    return vacancy


@pytest_asyncio.fixture()
async def dataset(db_session: AsyncSession, taxonomy_rows: None) -> dict[str, Any]:
    acme = Company(name="Acme", normalized_name="acme")
    beta = Company(name="Beta", normalized_name="beta")
    hh = Source(
        code="hh",
        name="hh.ru",
        kind=SourceKind.JSON_API,
        base_url="https://api.hh.ru",
        rate_limit_per_min=10,
    )
    remoteok = Source(
        code="remoteok",
        name="RemoteOK",
        kind=SourceKind.JSON_API,
        base_url="https://remoteok.com/api",
        rate_limit_per_min=10,
    )
    db_session.add_all([acme, beta, hh, remoteok])
    await db_session.flush()

    senior = await _add_vacancy(
        db_session,
        company=acme,
        source=hh,
        title="Senior Python Developer",
        work_format=WorkFormat.REMOTE,
        seniority=SeniorityLevel.SENIOR,
        language=VacancyLanguage.EN,
        published_at=datetime(2026, 11, 1, tzinfo=UTC),
        salary=5000,
        technologies=[("python", 3), ("fastapi", 2), ("docker", 1)],
    )
    junior = await _add_vacancy(
        db_session,
        company=beta,
        source=remoteok,
        title="Junior Django Developer",
        work_format=WorkFormat.OFFICE,
        seniority=SeniorityLevel.JUNIOR,
        language=VacancyLanguage.RU,
        published_at=datetime(2026, 11, 5, tzinfo=UTC),
        salary=1500,
        technologies=[("python", 1), ("django", 2)],
    )
    data = await _add_vacancy(
        db_session,
        company=acme,
        source=hh,
        title="Data Engineer",
        work_format=WorkFormat.HYBRID,
        seniority=SeniorityLevel.MIDDLE,
        language=VacancyLanguage.EN,
        published_at=datetime(2026, 10, 20, tzinfo=UTC),
        salary=None,
        technologies=[("python", 2), ("postgresql", 2)],
    )
    return {"senior": senior, "junior": junior, "data": data}


async def test_jobs_list_returns_page(
    api_client: httpx.AsyncClient, dataset: dict[str, Any]
) -> None:
    response = await api_client.get("/api/v1/jobs")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3
    assert body["limit"] == 20
    item = body["items"][0]
    assert item["company"]["name"]
    assert item["sources"][0]["source"] in {"hh", "remoteok"}
    assert isinstance(item["technologies"], list)


async def test_jobs_filter_by_technology(
    api_client: httpx.AsyncClient, dataset: dict[str, Any]
) -> None:
    response = await api_client.get("/api/v1/jobs", params={"technology": "django"})

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Junior Django Developer"


async def test_jobs_filter_by_seniority_and_format(
    api_client: httpx.AsyncClient, dataset: dict[str, Any]
) -> None:
    response = await api_client.get(
        "/api/v1/jobs", params={"seniority": "junior", "work_format": "office"}
    )

    assert response.json()["total"] == 1


async def test_jobs_filter_by_salary_and_source(
    api_client: httpx.AsyncClient, dataset: dict[str, Any]
) -> None:
    response = await api_client.get("/api/v1/jobs", params={"min_salary": 2000, "source": "hh"})

    body = response.json()
    assert body["total"] == 1
    assert Decimal(str(body["items"][0]["salary_monthly_eur"])) == Decimal("5000")


async def test_jobs_search_by_title(api_client: httpx.AsyncClient, dataset: dict[str, Any]) -> None:
    response = await api_client.get("/api/v1/jobs", params={"q": "django"})
    assert response.json()["total"] == 1


async def test_jobs_sort_by_salary_desc(
    api_client: httpx.AsyncClient, dataset: dict[str, Any]
) -> None:
    response = await api_client.get("/api/v1/jobs", params={"sort": "salary", "order": "desc"})

    salaries = [item["salary_monthly_eur"] for item in response.json()["items"]]
    assert Decimal(str(salaries[0])) == Decimal("5000")
    assert salaries[-1] is None


async def test_jobs_pagination(api_client: httpx.AsyncClient, dataset: dict[str, Any]) -> None:
    response = await api_client.get("/api/v1/jobs", params={"limit": 1, "offset": 1})

    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 1
    assert body["limit"] == 1
    assert body["offset"] == 1


async def test_jobs_reject_invalid_pagination(
    api_client: httpx.AsyncClient, dataset: dict[str, Any]
) -> None:
    response = await api_client.get("/api/v1/jobs", params={"limit": 0})

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "validation_error"


async def test_job_detail(api_client: httpx.AsyncClient, dataset: dict[str, Any]) -> None:
    job_id = dataset["senior"].id

    response = await api_client.get(f"/api/v1/jobs/{job_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(job_id)
    assert body["description"].startswith("Senior Python Developer")
    assert "created_at" in body


async def test_job_detail_not_found(api_client: httpx.AsyncClient, dataset: dict[str, Any]) -> None:
    response = await api_client.get(f"/api/v1/jobs/{uuid.uuid4()}")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "not_found"
    assert body["instance"].startswith("/api/v1/jobs/")


async def test_companies_are_ordered_by_vacancies(
    api_client: httpx.AsyncClient, dataset: dict[str, Any]
) -> None:
    response = await api_client.get("/api/v1/companies")

    body = response.json()
    assert body["total"] == 2
    assert body["items"][0]["name"] == "Acme"
    assert body["items"][0]["vacancy_count"] == 2


async def test_companies_filter(api_client: httpx.AsyncClient, dataset: dict[str, Any]) -> None:
    response = await api_client.get("/api/v1/companies", params={"q": "beta"})

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Beta"


async def test_technologies_ranked_by_demand(
    api_client: httpx.AsyncClient, dataset: dict[str, Any]
) -> None:
    response = await api_client.get("/api/v1/technologies", params={"limit": 5})

    body = response.json()
    assert body["total"] == 93
    assert body["items"][0]["slug"] == "python"
    assert body["items"][0]["vacancy_count"] == 3


async def test_stats_shape(api_client: httpx.AsyncClient, dataset: dict[str, Any]) -> None:
    response = await api_client.get("/api/v1/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["vacancies"]["total"] == 3
    assert body["vacancies"]["with_salary"] == 2
    assert body["vacancies"]["remote"] == 1
    assert body["top_technologies"][0]["slug"] == "python"
    assert body["top_technologies"][0]["count"] == 3
    assert len(body["sources"]) == 2
    assert body["analyses"]["analyses"] == 0
    assert body["collector_runs"]["last_status"] is None
