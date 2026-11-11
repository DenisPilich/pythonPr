"""Analysis use case: prefilter -> cache -> provider -> persist.

Ordering matters economically: hard filters and the database cache are checked
before any provider call, so an unchanged profile or an obviously-irrelevant
vacancy never costs a token.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from decimal import Decimal

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.errors import AIResponseError
from app.ai.prompts.v1 import PROMPT_VERSION
from app.ai.types import (
    AICompletion,
    AnalysisRequest,
    ProfileSnapshot,
    TechnologyRef,
    VacancySnapshot,
)
from app.core.config import Settings
from app.core.exceptions import AIProviderError, BudgetExceededError, NotFoundError
from app.domain.enums import Recommendation, SeniorityLevel, WorkFormat
from app.domain.money import to_eur
from app.domain.profile import PROFILE_HASH_FIELDS, compute_profile_hash
from app.models import AIAnalysis, UserProfile, Vacancy
from app.ports.ai_provider import AIProvider
from app.repositories.analyses import AnalysisRepository
from app.repositories.jobs import JobRepository
from app.repositories.profiles import ProfileRepository


logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class AnalysisOutcome:
    analysis: AIAnalysis
    cached: bool = False
    skipped: bool = False
    skip_reason: str | None = None


class AnalysisService:
    def __init__(
        self,
        session: AsyncSession,
        provider: AIProvider,
        settings: Settings,
        *,
        fallback: AIProvider | None = None,
    ) -> None:
        self._session = session
        self._provider = provider
        self._fallback_provider = fallback
        self._settings = settings
        self._analyses = AnalysisRepository(session)
        self._profiles = ProfileRepository(session)

    async def analyze(self, *, vacancy_id: uuid.UUID, user_id: uuid.UUID) -> AnalysisOutcome:
        vacancy = await JobRepository(self._session).get_job(vacancy_id)
        if vacancy is None:
            raise NotFoundError(f"Vacancy {vacancy_id} not found")

        profile = await self._profiles.get_by_user_id(user_id)
        if profile is None:
            raise NotFoundError("Profile not found; create it before analysing vacancies")

        profile_hash = self._profile_hash(profile)

        cached = await self._analyses.get_cached(vacancy_id, user_id, profile_hash, PROMPT_VERSION)
        if cached is not None:
            return AnalysisOutcome(analysis=cached, cached=True)

        skip_reason = self._prefilter(profile, vacancy)
        if skip_reason is not None:
            analysis = await self._persist_prefilter(
                vacancy_id=vacancy_id,
                user_id=user_id,
                profile_hash=profile_hash,
                reason=skip_reason,
            )
            return AnalysisOutcome(analysis=analysis, skipped=True, skip_reason=skip_reason)

        await self._enforce_budget()

        request = AnalysisRequest(
            profile=self._profile_snapshot(profile),
            vacancy=self._vacancy_snapshot(vacancy),
        )
        completion = await self._complete(request)

        analysis = AIAnalysis(
            vacancy_id=vacancy_id,
            user_id=user_id,
            profile_hash=profile_hash,
            prompt_version=PROMPT_VERSION,
            provider=completion.provider,
            model=completion.model,
            match_score=completion.analysis.match_score,
            experience_match=completion.analysis.experience_match,
            skills_match=completion.analysis.skills_match,
            missing_skills=list(completion.analysis.missing_skills),
            strong_matches=list(completion.analysis.strong_matches),
            red_flags=list(completion.analysis.red_flags),
            recommendation=completion.analysis.recommendation,
            reason=completion.analysis.reason,
            is_degraded=completion.degraded,
            prompt_tokens=completion.prompt_tokens,
            completion_tokens=completion.completion_tokens,
            cost_usd=completion.cost_usd,
            latency_ms=completion.latency_ms,
            raw_response=completion.raw_response,
        )
        await self._analyses.save(analysis)
        await self._analyses.track_user_vacancy(
            user_id=user_id,
            vacancy_id=vacancy_id,
            analysis_id=analysis.id,
            match_score=analysis.match_score,
        )
        logger.info(
            "vacancy_analysed",
            vacancy_id=str(vacancy_id),
            user_id=str(user_id),
            provider=analysis.provider,
            score=analysis.match_score,
            degraded=analysis.is_degraded,
            cost_usd=str(analysis.cost_usd),
        )
        return AnalysisOutcome(analysis=analysis)

    async def _complete(self, request: AnalysisRequest) -> AICompletion:
        try:
            return await self._provider.analyze(request)
        except AIResponseError as exc:
            logger.warning("ai_invalid_response", provider=self._provider.name, error=str(exc))
            try:
                return await self._provider.analyze(replace(request, repair_note=str(exc)[:500]))
            except Exception as repair_exc:
                return await self._use_fallback(request, repair_exc)
        except Exception as exc:
            return await self._use_fallback(request, exc)

    async def _use_fallback(self, request: AnalysisRequest, error: Exception) -> AICompletion:
        if self._fallback_provider is None:
            raise AIProviderError(f"AI provider {self._provider.name!r} failed: {error}") from error
        logger.warning(
            "ai_fallback_used",
            provider=self._provider.name,
            fallback=self._fallback_provider.name,
            error=type(error).__name__,
        )
        completion = await self._fallback_provider.analyze(request)
        return replace(completion, degraded=True)

    async def _enforce_budget(self) -> None:
        if self._provider.name == "mock":
            return
        spent = await self._analyses.daily_cost()
        limit = Decimal(str(self._settings.ai_daily_budget_usd))
        if spent >= limit:
            raise BudgetExceededError(f"Daily AI budget exhausted (spent ${spent}, limit ${limit})")

    async def _persist_prefilter(
        self,
        *,
        vacancy_id: uuid.UUID,
        user_id: uuid.UUID,
        profile_hash: str,
        reason: str,
    ) -> AIAnalysis:
        analysis = AIAnalysis(
            vacancy_id=vacancy_id,
            user_id=user_id,
            profile_hash=profile_hash,
            prompt_version=PROMPT_VERSION,
            provider="prefilter",
            model="rules-v1",
            match_score=0,
            experience_match="Filtered before AI analysis.",
            skills_match="",
            recommendation=Recommendation.SKIP,
            reason=reason[:2000],
            is_degraded=True,
        )
        await self._analyses.save(analysis)
        await self._analyses.track_user_vacancy(
            user_id=user_id,
            vacancy_id=vacancy_id,
            analysis_id=analysis.id,
            match_score=0,
        )
        return analysis

    @staticmethod
    def _prefilter(profile: UserProfile, vacancy: Vacancy) -> str | None:
        if (
            profile.target_seniority
            and vacancy.seniority is not SeniorityLevel.UNKNOWN
            and vacancy.seniority not in profile.target_seniority
        ):
            targets = ", ".join(level.value for level in profile.target_seniority)
            return f"Seniority {vacancy.seniority.value} is outside the target list ({targets})"

        if (
            profile.work_formats
            and vacancy.work_format is not WorkFormat.UNKNOWN
            and vacancy.work_format not in profile.work_formats
        ):
            formats = ", ".join(fmt.value for fmt in profile.work_formats)
            return (
                f"Work format {vacancy.work_format.value} is not in the preferred list ({formats})"
            )

        floor = to_eur(profile.min_salary_amount, profile.salary_currency)
        if (
            vacancy.salary_monthly_eur is not None
            and floor is not None
            and vacancy.salary_monthly_eur < floor
        ):
            return (
                f"Salary ~EUR {vacancy.salary_monthly_eur}/month is below the floor "
                f"~EUR {floor}/month"
            )
        return None

    @staticmethod
    def _profile_hash(profile: UserProfile) -> str:
        payload = {field: getattr(profile, field) for field in PROFILE_HASH_FIELDS}
        return compute_profile_hash(payload)

    @staticmethod
    def _profile_snapshot(profile: UserProfile) -> ProfileSnapshot:
        return ProfileSnapshot(
            headline=profile.headline,
            desired_positions=tuple(profile.desired_positions),
            target_seniority=tuple(profile.target_seniority),
            skills=tuple(profile.skills),
            preferred_stack=tuple(profile.preferred_stack),
            excluded_stack=tuple(profile.excluded_stack),
            english_level=profile.english_level,
            min_salary_amount=profile.min_salary_amount,
            salary_currency=profile.salary_currency,
            preferred_locations=tuple(profile.preferred_locations),
            work_formats=tuple(profile.work_formats),
            min_match_score=profile.min_match_score,
        )

    @staticmethod
    def _vacancy_snapshot(vacancy: Vacancy) -> VacancySnapshot:
        technologies = sorted(
            vacancy.technologies, key=lambda link: (-link.mentions, link.technology.slug)
        )
        return VacancySnapshot(
            title=vacancy.title,
            company=vacancy.company.name,
            description=vacancy.description_clean,
            location=vacancy.location_raw,
            work_format=vacancy.work_format,
            seniority=vacancy.seniority,
            language=vacancy.language,
            salary_min=vacancy.salary_min,
            salary_max=vacancy.salary_max,
            salary_currency=vacancy.salary_currency,
            salary_monthly_eur=vacancy.salary_monthly_eur,
            technologies=tuple(
                TechnologyRef(
                    name=link.technology.name,
                    slug=link.technology.slug,
                    is_required=link.is_required,
                    mentions=link.mentions,
                )
                for link in technologies
            ),
        )
