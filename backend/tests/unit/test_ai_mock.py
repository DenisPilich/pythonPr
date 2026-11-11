from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.ai.mock_provider import MockAIProvider
from app.ai.prompts.v1 import SYSTEM_PROMPT, build_user_prompt
from app.ai.schema import AIAnalysisResult
from app.ai.types import (
    AnalysisRequest,
    ProfileSnapshot,
    TechnologyRef,
    VacancySnapshot,
)
from app.domain.enums import (
    EnglishLevel,
    Recommendation,
    SeniorityLevel,
    VacancyLanguage,
    WorkFormat,
)


def profile(**overrides: object) -> ProfileSnapshot:
    values: dict[str, object] = {
        "headline": "Python backend developer",
        "desired_positions": ("Python Backend Developer",),
        "target_seniority": (SeniorityLevel.SENIOR,),
        "skills": ("Python", "FastAPI", "PostgreSQL"),
        "preferred_stack": ("FastAPI",),
        "excluded_stack": (),
        "english_level": EnglishLevel.B2,
        "min_salary_amount": 3000,
        "salary_currency": "EUR",
        "preferred_locations": ("Remote",),
        "work_formats": (WorkFormat.REMOTE,),
        "min_match_score": 70,
    }
    values.update(overrides)
    return ProfileSnapshot(**values)  # type: ignore[arg-type]


def vacancy(**overrides: object) -> VacancySnapshot:
    values: dict[str, object] = {
        "title": "Senior Python Developer",
        "company": "Acme",
        "description": "We build APIs with FastAPI and PostgreSQL.",
        "location": "Remote",
        "work_format": WorkFormat.REMOTE,
        "seniority": SeniorityLevel.SENIOR,
        "language": VacancyLanguage.EN,
        "salary_min": 60000,
        "salary_max": 80000,
        "salary_currency": "EUR",
        "salary_monthly_eur": Decimal("5000"),
        "technologies": (
            TechnologyRef("Python", "python", True, 3),
            TechnologyRef("FastAPI", "fastapi", True, 2),
            TechnologyRef("PostgreSQL", "postgresql", True, 1),
        ),
    }
    values.update(overrides)
    return VacancySnapshot(**values)  # type: ignore[arg-type]


async def test_strong_match_scores_high() -> None:
    result = await MockAIProvider().analyze(AnalysisRequest(profile=profile(), vacancy=vacancy()))

    analysis = result.analysis
    assert analysis.match_score >= 80
    assert analysis.recommendation is Recommendation.APPLY
    assert set(analysis.strong_matches) == {"Python", "FastAPI", "PostgreSQL"}
    assert analysis.missing_skills == []
    assert result.cost_usd == Decimal("0")
    assert result.provider == "mock"


async def test_missing_skills_are_listed() -> None:
    result = await MockAIProvider().analyze(
        AnalysisRequest(
            profile=profile(skills=("Python",)),
            vacancy=vacancy(
                technologies=(
                    TechnologyRef("Python", "python", True, 1),
                    TechnologyRef("Kubernetes", "kubernetes", True, 2),
                    TechnologyRef("Docker", "docker", True, 1),
                )
            ),
        )
    )

    assert set(result.analysis.missing_skills) == {"Kubernetes", "Docker"}
    assert result.analysis.match_score < 80


async def test_seniority_mismatch_is_a_red_flag() -> None:
    result = await MockAIProvider().analyze(
        AnalysisRequest(
            profile=profile(target_seniority=(SeniorityLevel.JUNIOR,)),
            vacancy=vacancy(seniority=SeniorityLevel.LEAD),
        )
    )

    assert any("Seniority" in flag for flag in result.analysis.red_flags)


async def test_salary_below_floor_is_a_red_flag() -> None:
    result = await MockAIProvider().analyze(
        AnalysisRequest(
            profile=profile(min_salary_amount=9000),
            vacancy=vacancy(salary_monthly_eur=Decimal("2000")),
        )
    )

    assert any("below the floor" in flag for flag in result.analysis.red_flags)
    assert result.analysis.match_score < 80


async def test_excluded_stack_is_a_red_flag() -> None:
    result = await MockAIProvider().analyze(
        AnalysisRequest(
            profile=profile(excluded_stack=("PHP",)),
            vacancy=vacancy(
                technologies=(TechnologyRef("PHP", "php", True, 2),),
            ),
        )
    )

    assert any("Excluded stack" in flag for flag in result.analysis.red_flags)


async def test_work_format_mismatch_is_a_red_flag() -> None:
    result = await MockAIProvider().analyze(
        AnalysisRequest(
            profile=profile(work_formats=(WorkFormat.REMOTE,)),
            vacancy=vacancy(work_format=WorkFormat.OFFICE),
        )
    )

    assert any("Work format" in flag for flag in result.analysis.red_flags)


async def test_score_is_deterministic() -> None:
    request = AnalysisRequest(profile=profile(), vacancy=vacancy())
    provider = MockAIProvider()
    first = await provider.analyze(request)
    second = await provider.analyze(request)
    assert first.analysis == second.analysis


def test_prompt_contains_profile_and_vacancy() -> None:
    prompt = build_user_prompt(AnalysisRequest(profile=profile(), vacancy=vacancy()))

    assert "Python backend developer" in prompt
    assert "Senior Python Developer" in prompt
    assert "Acme" in prompt
    assert "Technologies (* = required)" in prompt
    assert "Return the corrected JSON only" not in prompt


def test_prompt_truncates_long_description() -> None:
    request = AnalysisRequest(profile=profile(), vacancy=vacancy(description="word " * 5000))
    prompt = build_user_prompt(request)
    assert len(prompt) < 8000
    assert "…" in prompt


def test_repair_note_is_appended() -> None:
    request = AnalysisRequest(
        profile=profile(), vacancy=vacancy(), repair_note="match_score: not an integer"
    )
    assert "match_score: not an integer" in build_user_prompt(request)


def test_system_prompt_sets_the_rules() -> None:
    assert "match_score" in SYSTEM_PROMPT
    assert "Never invent skills" in SYSTEM_PROMPT


@pytest.mark.parametrize(
    "payload",
    [
        {"match_score": 150},
        {"recommendation": "maybe"},
    ],
)
def test_analysis_result_validation(payload: dict[str, object]) -> None:
    complete: dict[str, object] = {
        "match_score": 80,
        "experience_match": "ok",
        "skills_match": "ok",
        "recommendation": "apply",
        "reason": "fine",
    }
    complete.update(payload)
    with pytest.raises(ValidationError):
        AIAnalysisResult.model_validate(complete)


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        AIAnalysisResult.model_validate(
            {
                "match_score": 80,
                "experience_match": "ok",
                "skills_match": "ok",
                "recommendation": "apply",
                "reason": "fine",
                "confidence": 0.9,
            }
        )


def test_required_fields_are_enforced() -> None:
    with pytest.raises(ValidationError):
        AIAnalysisResult.model_validate({"match_score": 50})
