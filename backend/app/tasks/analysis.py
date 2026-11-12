"""Analysis tasks: find (vacancy, profile) pairs that need a verdict, then score them."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompts.v1 import PROMPT_VERSION
from app.core.config import Settings
from app.core.exceptions import AIProviderError
from app.db.session import Database
from app.models import AIAnalysis, User, UserProfile, Vacancy
from app.ports.ai_provider import AIProvider
from app.services.analysis import AnalysisService
from app.tasks.celery_app import celery_app
from app.tasks.runtime import get_runtime, run_async


async def pending_analysis_pairs(
    session: AsyncSession,
    *,
    limit: int = 50,
    lookback_days: int = 14,
) -> list[tuple[uuid.UUID, uuid.UUID]]:
    since = datetime.now(UTC) - timedelta(days=lookback_days)
    statement = (
        select(Vacancy.id, UserProfile.user_id)
        .select_from(UserProfile)
        .join(User, User.id == UserProfile.user_id)
        .join(Vacancy, Vacancy.is_active.is_(True))
        .where(
            User.is_active.is_(True),
            Vacancy.first_seen_at >= since,
            ~exists().where(
                AIAnalysis.vacancy_id == Vacancy.id,
                AIAnalysis.user_id == UserProfile.user_id,
                AIAnalysis.profile_hash == UserProfile.profile_hash,
                AIAnalysis.prompt_version == PROMPT_VERSION,
            ),
        )
        .order_by(Vacancy.published_at.desc().nulls_last(), Vacancy.id)
        .limit(limit)
    )
    rows = (await session.execute(statement)).all()
    return [(row[0], row[1]) for row in rows]


async def analyze_vacancy_async(
    vacancy_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    database: Database,
    provider: AIProvider,
    settings: Settings,
    fallback: AIProvider | None = None,
) -> dict[str, Any]:
    async with database.session() as session:
        service = AnalysisService(session, provider, settings, fallback=fallback)
        outcome = await service.analyze(vacancy_id=vacancy_id, user_id=user_id)
    analysis = outcome.analysis
    return {
        "vacancy_id": str(vacancy_id),
        "user_id": str(user_id),
        "analysis_id": str(analysis.id),
        "score": analysis.match_score,
        "recommendation": analysis.recommendation.value,
        "provider": analysis.provider,
        "cached": outcome.cached,
        "skipped": outcome.skipped,
    }


async def count_pending_pairs(session: AsyncSession, *, lookback_days: int = 14) -> int:
    return len(await pending_analysis_pairs(session, limit=1000, lookback_days=lookback_days))


@celery_app.task(
    bind=True,
    name="app.tasks.analysis.analyze_vacancy",
    autoretry_for=(AIProviderError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=2,
    soft_time_limit=180,
)
def analyze_vacancy(self: Any, vacancy_id: str, user_id: str) -> dict[str, Any]:
    runtime = get_runtime()
    return run_async(
        analyze_vacancy_async(
            uuid.UUID(vacancy_id),
            uuid.UUID(user_id),
            database=runtime.database,
            provider=runtime.provider,
            settings=runtime.settings,
            fallback=runtime.fallback,
        )
    )


@celery_app.task(name="app.tasks.analysis.analyze_new_vacancies")
def analyze_new_vacancies() -> dict[str, int]:
    runtime = get_runtime()

    async def _collect() -> list[tuple[uuid.UUID, uuid.UUID]]:
        async with runtime.database.session() as session:
            return await pending_analysis_pairs(
                session,
                limit=runtime.settings.ai_max_analyses_per_run,
                lookback_days=runtime.settings.analysis_lookback_days,
            )

    pairs = run_async(_collect())
    for vacancy_id, user_id in pairs:
        analyze_vacancy.delay(str(vacancy_id), str(user_id))
    return {"queued": len(pairs)}
