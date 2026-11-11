"""Request/response types for the AI layer.

These are deliberately provider-neutral: the prompt builder, the mock scorer and
the OpenAI adapter all speak the same `AnalysisRequest` / `AICompletion` pair.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.ai.schema import AIAnalysisResult
from app.domain.enums import EnglishLevel, SeniorityLevel, VacancyLanguage, WorkFormat


@dataclass(frozen=True, slots=True)
class TechnologyRef:
    name: str
    slug: str
    is_required: bool
    mentions: int


@dataclass(frozen=True, slots=True)
class ProfileSnapshot:
    headline: str | None
    desired_positions: tuple[str, ...]
    target_seniority: tuple[SeniorityLevel, ...]
    skills: tuple[str, ...]
    preferred_stack: tuple[str, ...]
    excluded_stack: tuple[str, ...]
    english_level: EnglishLevel
    min_salary_amount: int | None
    salary_currency: str
    preferred_locations: tuple[str, ...]
    work_formats: tuple[WorkFormat, ...]
    min_match_score: int


@dataclass(frozen=True, slots=True)
class VacancySnapshot:
    title: str
    company: str
    description: str
    location: str | None
    work_format: WorkFormat
    seniority: SeniorityLevel
    language: VacancyLanguage
    salary_min: int | None
    salary_max: int | None
    salary_currency: str | None
    salary_monthly_eur: Decimal | None
    technologies: tuple[TechnologyRef, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class AnalysisRequest:
    profile: ProfileSnapshot
    vacancy: VacancySnapshot
    repair_note: str | None = None


@dataclass(frozen=True, slots=True)
class AICompletion:
    analysis: AIAnalysisResult
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: Decimal = Decimal("0")
    latency_ms: int = 0
    raw_response: dict[str, Any] | None = None
    degraded: bool = False
