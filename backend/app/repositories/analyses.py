"""Analysis persistence: cache lookup, cost accounting, user tracking."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import UserVacancyStatus
from app.models import AIAnalysis, UserVacancy


class AnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_cached(
        self,
        vacancy_id: uuid.UUID,
        user_id: uuid.UUID,
        profile_hash: str,
        prompt_version: str,
    ) -> AIAnalysis | None:
        return await self._session.scalar(
            select(AIAnalysis).where(
                AIAnalysis.vacancy_id == vacancy_id,
                AIAnalysis.user_id == user_id,
                AIAnalysis.profile_hash == profile_hash,
                AIAnalysis.prompt_version == prompt_version,
            )
        )

    async def latest(self, vacancy_id: uuid.UUID, user_id: uuid.UUID) -> AIAnalysis | None:
        return await self._session.scalar(
            select(AIAnalysis)
            .where(
                AIAnalysis.vacancy_id == vacancy_id,
                AIAnalysis.user_id == user_id,
            )
            .order_by(AIAnalysis.created_at.desc())
            .limit(1)
        )

    async def daily_cost(self) -> Decimal:
        start_of_day = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        total = await self._session.scalar(
            select(func.coalesce(func.sum(AIAnalysis.cost_usd), 0)).where(
                AIAnalysis.created_at >= start_of_day
            )
        )
        return Decimal(str(total or 0))

    async def save(self, analysis: AIAnalysis) -> AIAnalysis:
        self._session.add(analysis)
        await self._session.flush()
        await self._session.refresh(analysis)
        return analysis

    async def track_user_vacancy(
        self,
        *,
        user_id: uuid.UUID,
        vacancy_id: uuid.UUID,
        analysis_id: uuid.UUID,
        match_score: int,
    ) -> None:
        statement = pg_insert(UserVacancy).values(
            user_id=user_id,
            vacancy_id=vacancy_id,
            ai_analysis_id=analysis_id,
            status=UserVacancyStatus.NEW,
            match_score=match_score,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[UserVacancy.user_id, UserVacancy.vacancy_id],
            set_={
                "ai_analysis_id": analysis_id,
                "match_score": match_score,
                "updated_at": func.now(),
            },
        )
        await self._session.execute(statement)
