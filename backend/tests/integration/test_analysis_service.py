from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.errors import AIResponseError
from app.ai.mock_provider import MockAIProvider
from app.ai.types import AICompletion, AnalysisRequest
from app.core.config import Settings
from app.core.exceptions import AIProviderError, BudgetExceededError, NotFoundError
from app.domain.enums import (
    EnglishLevel,
    Recommendation,
    SalaryPeriod,
    SeniorityLevel,
    SourceKind,
    UserVacancyStatus,
    VacancyLanguage,
    WorkFormat,
)
from app.domain.profile import compute_profile_hash
from app.models import (
    AIAnalysis,
    Company,
    Source,
    Technology,
    User,
    UserProfile,
    UserVacancy,
    Vacancy,
    VacancySource,
    VacancyTechnology,
)
from app.services.analysis import AnalysisService


pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("taxonomy_rows")]


def profile_fields(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "headline": "Python backend developer",
        "desired_positions": ["Python Backend Developer"],
        "target_seniority": [SeniorityLevel.SENIOR],
        "skills": ["Python", "FastAPI"],
        "preferred_stack": ["FastAPI"],
        "excluded_stack": [],
        "english_level": EnglishLevel.B2,
        "min_salary_amount": 3000,
        "salary_currency": "EUR",
        "preferred_locations": ["Remote"],
        "work_formats": [WorkFormat.REMOTE],
        "min_match_score": 70,
        "notifications_enabled": True,
        "max_notifications_per_day": 10,
    }
    values.update(overrides)
    return values


async def create_profile(
    session: AsyncSession, telegram_id: int = 9001, **overrides: Any
) -> tuple[User, UserProfile]:
    fields = profile_fields(**overrides)
    user = User(telegram_id=telegram_id)
    session.add(user)
    await session.flush()
    profile = UserProfile(
        user_id=user.id,
        profile_hash=compute_profile_hash(fields),
        **fields,
    )
    session.add(profile)
    await session.flush()
    return user, profile


async def create_vacancy(
    session: AsyncSession,
    *,
    title: str = "Senior Python Developer",
    work_format: WorkFormat = WorkFormat.REMOTE,
    seniority: SeniorityLevel = SeniorityLevel.SENIOR,
    salary: int = 5000,
    technologies: tuple[tuple[str, bool], ...] = (("python", True), ("fastapi", True)),
) -> Vacancy:
    company = Company(name="Acme", normalized_name="acme")
    source = Source(
        code="hh",
        name="hh.ru",
        kind=SourceKind.JSON_API,
        base_url="https://api.hh.ru",
        rate_limit_per_min=10,
    )
    session.add_all([company, source])
    await session.flush()

    vacancy = Vacancy(
        company_id=company.id,
        title=title,
        description_clean="We build APIs with Python and FastAPI.",
        description_raw="<p>We build APIs with Python and FastAPI.</p>",
        fingerprint=hashlib.sha256(title.encode()).hexdigest(),
        content_hash=hashlib.sha256(title.encode()).hexdigest(),
        work_format=work_format,
        seniority=seniority,
        language=VacancyLanguage.EN,
        salary_min=salary,
        salary_max=salary,
        salary_currency="EUR",
        salary_period=SalaryPeriod.MONTH,
        salary_monthly_eur=Decimal(salary),
        published_at=datetime(2026, 11, 1, tzinfo=UTC),
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

    technology_rows = {
        technology.slug: technology
        for technology in (await session.scalars(select(Technology))).all()
    }
    for slug, required in technologies:
        session.add(
            VacancyTechnology(
                vacancy_id=vacancy.id,
                technology_id=technology_rows[slug].id,
                is_required=required,
                mentions=1,
            )
        )
    await session.flush()
    return vacancy


@pytest_asyncio.fixture()
async def scenario(db_session: AsyncSession) -> tuple[User, UserProfile, Vacancy]:
    user, profile = await create_profile(db_session)
    vacancy = await create_vacancy(db_session)
    return user, profile, vacancy


class ExplodingProvider:
    name = "mock"

    def __init__(self) -> None:
        self.calls = 0

    async def analyze(self, request: AnalysisRequest) -> AICompletion:
        self.calls += 1
        raise AssertionError("provider must not be called")

    async def aclose(self) -> None:
        return None


class FailingProvider:
    name = "openai"

    def __init__(self) -> None:
        self.calls = 0

    async def analyze(self, request: AnalysisRequest) -> AICompletion:
        self.calls += 1
        raise AIProviderError("provider is down")

    async def aclose(self) -> None:
        return None


class FlakyProvider:
    name = "openai"

    def __init__(self) -> None:
        self.calls = 0
        self._mock = MockAIProvider()

    async def analyze(self, request: AnalysisRequest) -> AICompletion:
        self.calls += 1
        if self.calls == 1:
            raise AIResponseError("match_score must be an integer")
        return await self._mock.analyze(request)

    async def aclose(self) -> None:
        return None


class PaidMockProvider(MockAIProvider):
    """Mock output, but accounted as a paid provider for budget tests."""

    name = "openai"


async def test_analysis_is_persisted_and_tracked(
    db_session: AsyncSession,
    scenario: tuple[User, UserProfile, Vacancy],
    settings: Settings,
) -> None:
    user, _, vacancy = scenario
    service = AnalysisService(db_session, MockAIProvider(), settings)

    outcome = await service.analyze(vacancy_id=vacancy.id, user_id=user.id)

    assert outcome.cached is False
    assert outcome.skipped is False
    assert outcome.analysis.provider == "mock"
    assert outcome.analysis.match_score >= 75
    assert outcome.analysis.recommendation is Recommendation.APPLY

    tracked = await db_session.scalar(
        select(UserVacancy).where(
            UserVacancy.user_id == user.id, UserVacancy.vacancy_id == vacancy.id
        )
    )
    assert tracked is not None
    assert tracked.status is UserVacancyStatus.NEW
    assert tracked.match_score == outcome.analysis.match_score


async def test_second_analysis_is_served_from_cache(
    db_session: AsyncSession,
    scenario: tuple[User, UserProfile, Vacancy],
    settings: Settings,
) -> None:
    user, _, vacancy = scenario
    service = AnalysisService(db_session, MockAIProvider(), settings)

    first = await service.analyze(vacancy_id=vacancy.id, user_id=user.id)
    second = await service.analyze(vacancy_id=vacancy.id, user_id=user.id)

    assert second.cached is True
    assert second.analysis.id == first.analysis.id
    count = await db_session.scalar(select(func.count()).select_from(AIAnalysis))
    assert count == 1


async def test_prefilter_skips_the_provider(db_session: AsyncSession, settings: Settings) -> None:
    user, _ = await create_profile(
        db_session, telegram_id=9002, target_seniority=[SeniorityLevel.JUNIOR]
    )
    vacancy = await create_vacancy(db_session, title="Lead Engineer", seniority=SeniorityLevel.LEAD)
    provider = ExplodingProvider()
    service = AnalysisService(db_session, provider, settings)  # type: ignore[arg-type]

    outcome = await service.analyze(vacancy_id=vacancy.id, user_id=user.id)

    assert outcome.skipped is True
    assert outcome.skip_reason is not None and "Seniority" in outcome.skip_reason
    assert outcome.analysis.provider == "prefilter"
    assert outcome.analysis.match_score == 0
    assert outcome.analysis.recommendation is Recommendation.SKIP
    assert provider.calls == 0


async def test_budget_exhaustion_blocks_paid_provider(
    db_session: AsyncSession,
    scenario: tuple[User, UserProfile, Vacancy],
    settings: Settings,
) -> None:
    user, _, vacancy = scenario
    db_session.add(
        AIAnalysis(
            vacancy_id=vacancy.id,
            user_id=user.id,
            profile_hash="x" * 64,
            prompt_version="v0",
            provider="openai",
            model="gpt-4o-mini",
            match_score=50,
            recommendation=Recommendation.CONSIDER,
            reason="previous run",
            cost_usd=Decimal("5"),
        )
    )
    await db_session.flush()

    service = AnalysisService(
        db_session,
        PaidMockProvider(),
        settings.model_copy(update={"ai_daily_budget_usd": 1.0}),
    )

    with pytest.raises(BudgetExceededError):
        await service.analyze(vacancy_id=vacancy.id, user_id=user.id)


async def test_provider_failure_falls_back_to_mock(
    db_session: AsyncSession,
    scenario: tuple[User, UserProfile, Vacancy],
    settings: Settings,
) -> None:
    user, _, vacancy = scenario
    provider = FailingProvider()
    fallback = MockAIProvider()
    service = AnalysisService(db_session, provider, settings, fallback=fallback)  # type: ignore[arg-type]

    outcome = await service.analyze(vacancy_id=vacancy.id, user_id=user.id)

    assert provider.calls == 1
    assert outcome.analysis.provider == "mock"
    assert outcome.analysis.is_degraded is True


async def test_invalid_response_is_repaired_once(
    db_session: AsyncSession,
    scenario: tuple[User, UserProfile, Vacancy],
    settings: Settings,
) -> None:
    user, _, vacancy = scenario
    provider = FlakyProvider()
    service = AnalysisService(db_session, provider, settings)  # type: ignore[arg-type]

    outcome = await service.analyze(vacancy_id=vacancy.id, user_id=user.id)

    assert provider.calls == 2
    assert outcome.analysis.provider == "mock"
    assert outcome.analysis.is_degraded is False


async def test_missing_profile_or_vacancy(
    db_session: AsyncSession,
    scenario: tuple[User, UserProfile, Vacancy],
    settings: Settings,
) -> None:
    user, _, vacancy = scenario
    service = AnalysisService(db_session, MockAIProvider(), settings)

    with pytest.raises(NotFoundError):
        await service.analyze(vacancy_id=vacancy.id, user_id=uuid.uuid4())

    with pytest.raises(NotFoundError):
        await service.analyze(vacancy_id=uuid.uuid4(), user_id=user.id)
