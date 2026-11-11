from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import httpx
import pytest
import respx

from app.ai.errors import AIResponseError
from app.ai.openai_provider import OpenAIProvider
from app.ai.types import (
    AnalysisRequest,
    ProfileSnapshot,
    TechnologyRef,
    VacancySnapshot,
)
from app.core.config import Settings
from app.core.exceptions import AIProviderError, ConfigurationError
from app.domain.enums import EnglishLevel, SeniorityLevel, VacancyLanguage, WorkFormat


URL = "https://llm.test/v1/chat/completions"

ANALYSIS: dict[str, Any] = {
    "match_score": 87,
    "experience_match": "Senior level fits.",
    "skills_match": "Python and FastAPI match.",
    "missing_skills": ["Docker"],
    "strong_matches": ["Python", "FastAPI"],
    "red_flags": [],
    "recommendation": "apply",
    "reason": "Strong stack overlap and a remote format.",
}


def settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "_env_file": None,
        "environment": "test",
        "ai_provider": "openai",
        "openai_api_key": "sk-test",
        "openai_base_url": "https://llm.test/v1",
        "ai_model": "gpt-4o-mini",
        "ai_max_retries": 0,
    }
    values.update(overrides)
    return Settings(**values)


def request() -> AnalysisRequest:
    return AnalysisRequest(
        profile=ProfileSnapshot(
            headline="Backend",
            desired_positions=("Backend Developer",),
            target_seniority=(SeniorityLevel.SENIOR,),
            skills=("Python", "FastAPI"),
            preferred_stack=(),
            excluded_stack=(),
            english_level=EnglishLevel.B2,
            min_salary_amount=3000,
            salary_currency="EUR",
            preferred_locations=(),
            work_formats=(WorkFormat.REMOTE,),
            min_match_score=70,
        ),
        vacancy=VacancySnapshot(
            title="Senior Python Developer",
            company="Acme",
            description="FastAPI and PostgreSQL.",
            location="Remote",
            work_format=WorkFormat.REMOTE,
            seniority=SeniorityLevel.SENIOR,
            language=VacancyLanguage.EN,
            salary_min=60000,
            salary_max=80000,
            salary_currency="EUR",
            salary_monthly_eur=Decimal("5000"),
            technologies=(TechnologyRef("Python", "python", True, 1),),
        ),
    )


def completion_response(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": "gpt-4o-mini",
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 1000, "completion_tokens": 200},
        },
    )


async def test_successful_structured_output() -> None:
    provider = OpenAIProvider(settings())
    try:
        with respx.mock:
            route = respx.post(URL).mock(return_value=completion_response(json.dumps(ANALYSIS)))
            completion = await provider.analyze(request())
    finally:
        await provider.aclose()

    assert route.call_count == 1
    assert completion.analysis.match_score == 87
    assert completion.provider == "openai"
    assert completion.prompt_tokens == 1000
    assert completion.completion_tokens == 200
    assert completion.cost_usd == Decimal("0.00027")
    assert completion.degraded is False


async def test_invalid_json_raises_response_error() -> None:
    provider = OpenAIProvider(settings())
    try:
        with respx.mock:
            respx.post(URL).mock(return_value=completion_response("Sure! Here is my analysis..."))
            with pytest.raises(AIResponseError):
                await provider.analyze(request())
    finally:
        await provider.aclose()


async def test_schema_violation_raises_response_error() -> None:
    provider = OpenAIProvider(settings())
    try:
        with respx.mock:
            respx.post(URL).mock(
                return_value=completion_response(json.dumps({**ANALYSIS, "match_score": 150}))
            )
            with pytest.raises(AIResponseError):
                await provider.analyze(request())
    finally:
        await provider.aclose()


async def test_retries_on_server_error() -> None:
    provider = OpenAIProvider(settings(ai_max_retries=1))
    try:
        with respx.mock:
            route = respx.post(URL).mock(
                side_effect=[
                    httpx.Response(500),
                    completion_response(json.dumps(ANALYSIS)),
                ]
            )
            completion = await provider.analyze(request())
    finally:
        await provider.aclose()

    assert route.call_count == 2
    assert completion.analysis.match_score == 87


async def test_auth_error_is_not_retried() -> None:
    provider = OpenAIProvider(settings())
    try:
        with respx.mock:
            route = respx.post(URL).mock(return_value=httpx.Response(401, text="bad key"))
            with pytest.raises(AIProviderError):
                await provider.analyze(request())
    finally:
        await provider.aclose()

    assert route.call_count == 1


def test_requires_api_key() -> None:
    with pytest.raises(ConfigurationError):
        OpenAIProvider(settings(openai_api_key=None))
