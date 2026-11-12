from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.bot.texts import (
    help_text,
    profile_text,
    start_text,
    stats_text,
    vacancy_card_text,
)
from app.domain.enums import (
    EnglishLevel,
    Recommendation,
    SalaryPeriod,
    SeniorityLevel,
    UserVacancyStatus,
    VacancyLanguage,
    WorkFormat,
)
from app.models import AIAnalysis, Company, UserProfile, UserVacancy, Vacancy
from app.schemas.stats import (
    AnalysisSummary,
    CollectorRunsSummary,
    DistributionItem,
    SourceStat,
    StatsResponse,
    VacancyTotals,
)


def make_profile(**overrides: object) -> UserProfile:
    values: dict[str, object] = {
        "user_id": uuid.uuid4(),
        "profile_hash": "h" * 64,
        "headline": "Python backend",
        "desired_positions": ["Backend Developer"],
        "target_seniority": [SeniorityLevel.JUNIOR, SeniorityLevel.MIDDLE],
        "skills": ["Python", "FastAPI"],
        "preferred_stack": ["FastAPI"],
        "excluded_stack": [],
        "english_level": EnglishLevel.B2,
        "min_salary_amount": 2500,
        "salary_currency": "EUR",
        "preferred_locations": ["Remote"],
        "work_formats": [WorkFormat.REMOTE],
        "min_match_score": 70,
    }
    values.update(overrides)
    return UserProfile(**values)  # type: ignore[arg-type]


def make_vacancy() -> Vacancy:
    company = Company(id=uuid.uuid4(), name="Acme", normalized_name="acme")
    return Vacancy(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Senior Python Developer",
        description_clean="Python, FastAPI",
        description_raw="<p>Python, FastAPI</p>",
        fingerprint="f" * 64,
        content_hash="c" * 64,
        company=company,
        work_format=WorkFormat.REMOTE,
        seniority=SeniorityLevel.SENIOR,
        language=VacancyLanguage.EN,
        salary_min=5000,
        salary_max=5000,
        salary_currency="EUR",
        salary_period=SalaryPeriod.MONTH,
        salary_monthly_eur=Decimal("5000"),
    )


def test_start_text_escapes_name() -> None:
    text = start_text("<Denis>")
    assert "&lt;Denis&gt;" in text
    assert "AI Job Radar" in text


def test_help_lists_commands() -> None:
    for command in ("/profile", "/jobs", "/top", "/stats", "/settings"):
        assert command in help_text()


def test_profile_text_contains_key_fields() -> None:
    text = profile_text(make_profile())
    assert "Python, FastAPI" in text
    assert "junior, middle" in text
    assert "2500 EUR" in text
    assert "70%" in text


def test_vacancy_card_contains_score_and_company() -> None:
    vacancy = make_vacancy()
    analysis = AIAnalysis(
        id=uuid.uuid4(),
        vacancy_id=vacancy.id,
        user_id=uuid.uuid4(),
        profile_hash="h" * 64,
        prompt_version="v1",
        provider="mock",
        model="heuristic-v1",
        match_score=87,
        recommendation=Recommendation.APPLY,
        reason="good",
    )
    text = vacancy_card_text(vacancy, analysis=analysis)
    assert "<b>Senior Python Developer</b>" in text
    assert "Acme" in text
    assert "87%" in text
    assert "APPLY" in text


def test_stats_text_includes_personal_history() -> None:
    stats = StatsResponse(
        generated_at=datetime.now(UTC),
        vacancies=VacancyTotals(
            total=10,
            active=9,
            with_salary=4,
            new_last_7_days=3,
            remote=5,
            remote_share=0.5,
        ),
        sources=[
            SourceStat(
                code="hh",
                name="hh.ru",
                is_enabled=True,
                vacancies=10,
                last_success_at=None,
                last_run_status="success",
            )
        ],
        top_technologies=[],
        top_companies=[],
        seniority=[DistributionItem(key="senior", count=4, share=0.4)],
        work_formats=[],
        languages=[],
        analyses=AnalysisSummary(analyses=0, average_match_score=None),
        collector_runs=CollectorRunsSummary(last_24h=1, failed_last_24h=0, last_status="success"),
    )

    text = stats_text(stats, {"sent": 2, "applied": 1})

    assert "Всего вакансий: <b>10</b>" in text
    assert "Applied: 1" in text


def test_vacancy_card_handles_missing_analysis() -> None:
    vacancy = make_vacancy()
    tracked = UserVacancy(
        user_id=uuid.uuid4(),
        vacancy_id=vacancy.id,
        match_score=55,
        status=UserVacancyStatus.NEW,
    )
    text = vacancy_card_text(vacancy, analysis=None, status=tracked)
    assert "55%" in text
    assert "new" in text
