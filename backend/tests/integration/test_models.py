from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete, func, insert, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.enums import (
    CollectorRunStatus,
    EnglishLevel,
    SeniorityLevel,
    SourceKind,
    TechnologyCategory,
    WorkFormat,
)
from app.models import (
    CollectorRun,
    Company,
    Source,
    Technology,
    User,
    UserProfile,
    Vacancy,
    VacancySource,
    VacancyTechnology,
)


pytestmark = pytest.mark.integration


async def create_company(session: AsyncSession, name: str = "Acme") -> Company:
    company = Company(name=name, normalized_name=name.lower())
    session.add(company)
    await session.flush()
    return company


def vacancy_kwargs(company_id: uuid.UUID, **overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "company_id": company_id,
        "title": "Python Backend Developer",
        "fingerprint": "f" * 64,
        "content_hash": "c" * 64,
    }
    values.update(overrides)
    return values


async def test_profile_arrays_round_trip(db_session: AsyncSession) -> None:
    user = User(telegram_id=5001, username="dev")
    user.profile = UserProfile(
        profile_hash="h" * 64,
        skills=["Python", "FastAPI"],
        preferred_stack=["FastAPI"],
        target_seniority=[SeniorityLevel.JUNIOR, SeniorityLevel.MIDDLE],
        work_formats=[WorkFormat.REMOTE, WorkFormat.HYBRID],
        english_level=EnglishLevel.B2,
        min_salary_amount=2500,
    )
    db_session.add(user)
    await db_session.flush()

    loaded = await db_session.scalar(
        select(User)
        .where(User.id == user.id)
        .options(selectinload(User.profile))
        .execution_options(populate_existing=True)
    )
    assert loaded is not None
    assert loaded.profile is not None
    assert loaded.profile.skills == ["Python", "FastAPI"]
    assert loaded.profile.target_seniority == [SeniorityLevel.JUNIOR, SeniorityLevel.MIDDLE]
    assert loaded.profile.work_formats == [WorkFormat.REMOTE, WorkFormat.HYBRID]
    assert loaded.profile.english_level is EnglishLevel.B2
    assert loaded.profile.min_salary_amount == 2500


async def test_deleting_user_cascades_to_profile(db_session: AsyncSession) -> None:
    user = User(telegram_id=5002)
    user.profile = UserProfile(profile_hash="h" * 64)
    db_session.add(user)
    await db_session.flush()

    await db_session.execute(delete(User).where(User.id == user.id))

    remaining = await db_session.scalar(
        select(func.count()).select_from(UserProfile).where(UserProfile.user_id == user.id)
    )
    assert remaining == 0


async def test_vacancy_fingerprint_is_unique(db_session: AsyncSession) -> None:
    company = await create_company(db_session)
    db_session.add(Vacancy(**vacancy_kwargs(company.id)))  # type: ignore[arg-type]
    await db_session.flush()

    db_session.add(
        Vacancy(**vacancy_kwargs(company.id, title="Another title"))  # type: ignore[arg-type]
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_company_normalized_name_is_unique(db_session: AsyncSession) -> None:
    await create_company(db_session, name="Acme")
    db_session.add(Company(name="ACME LLC", normalized_name="acme"))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_search_vector_is_generated(db_session: AsyncSession) -> None:
    company = await create_company(db_session)
    vacancy = Vacancy(
        **vacancy_kwargs(  # type: ignore[arg-type]
            company.id,
            title="Senior Python Engineer",
            description_clean="We use FastAPI, PostgreSQL and Docker.",
        )
    )
    db_session.add(vacancy)
    await db_session.flush()

    found = await db_session.scalar(
        select(Vacancy.id)
        .where(text("search_vector @@ plainto_tsquery('simple', :term)"))
        .params(term="fastapi")
    )
    assert found == vacancy.id


async def test_vacancy_defaults_are_applied(db_session: AsyncSession) -> None:
    company = await create_company(db_session)
    vacancy = Vacancy(**vacancy_kwargs(company.id))  # type: ignore[arg-type]
    db_session.add(vacancy)
    await db_session.flush()
    await db_session.refresh(vacancy)

    assert vacancy.work_format is WorkFormat.UNKNOWN
    assert vacancy.seniority is SeniorityLevel.UNKNOWN
    assert vacancy.is_active is True
    assert vacancy.fingerprint_version == 1
    assert vacancy.created_at is not None


async def test_source_external_id_is_unique_per_source(db_session: AsyncSession) -> None:
    source = Source(code="test-source", name="Test", kind=SourceKind.JSON_API)
    company = await create_company(db_session)
    vacancy = Vacancy(**vacancy_kwargs(company.id))  # type: ignore[arg-type]
    db_session.add_all([source, vacancy])
    await db_session.flush()

    db_session.add(
        VacancySource(
            vacancy_id=vacancy.id,
            source_id=source.id,
            external_id="42",
            url="https://example.com/jobs/42",
        )
    )
    await db_session.flush()

    db_session.add(
        VacancySource(
            vacancy_id=vacancy.id,
            source_id=source.id,
            external_id="42",
            url="https://example.com/jobs/42?utm_source=x",
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_vacancy_technology_duplicate_is_rejected(db_session: AsyncSession) -> None:
    company = await create_company(db_session)
    vacancy = Vacancy(**vacancy_kwargs(company.id))  # type: ignore[arg-type]
    technology = Technology(
        slug="python",
        name="Python",
        category=TechnologyCategory.LANGUAGE,
        aliases=["python"],
    )
    db_session.add_all([vacancy, technology])
    await db_session.flush()

    await db_session.execute(
        insert(VacancyTechnology).values(
            vacancy_id=vacancy.id, technology_id=technology.id, is_required=True, mentions=3
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.execute(
            insert(VacancyTechnology).values(vacancy_id=vacancy.id, technology_id=technology.id)
        )
    await db_session.rollback()


async def test_collector_run_tracks_lifecycle_defaults(db_session: AsyncSession) -> None:
    source = Source(code="runs", name="Runs", kind=SourceKind.RSS)
    db_session.add(source)
    await db_session.flush()

    run = CollectorRun(source_id=source.id, celery_task_id="task-1")
    db_session.add(run)
    await db_session.flush()
    await db_session.refresh(run)

    assert run.status is CollectorRunStatus.RUNNING
    assert run.items_fetched == 0
    assert run.started_at is not None
