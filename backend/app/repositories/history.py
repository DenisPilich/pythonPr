"""Per-user vacancy history queries for the dashboard."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.enums import UserVacancyStatus
from app.models import Company, UserVacancy, Vacancy, VacancySource, VacancyTechnology


class HistoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        status: UserVacancyStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[tuple[UserVacancy, Vacancy]], int]:
        conditions = [UserVacancy.user_id == user_id]
        if status is not None:
            conditions.append(UserVacancy.status == status)

        total = await self._session.scalar(
            select(func.count()).select_from(UserVacancy).where(*conditions)
        )
        statement = (
            select(UserVacancy, Vacancy)
            .join(Vacancy, Vacancy.id == UserVacancy.vacancy_id)
            .join(Company, Company.id == Vacancy.company_id)
            .where(*conditions)
            .options(
                selectinload(Vacancy.company),
                selectinload(Vacancy.sources).selectinload(VacancySource.source),
                selectinload(Vacancy.technologies).selectinload(VacancyTechnology.technology),
            )
            .order_by(UserVacancy.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(statement)).all()
        return [(row[0], row[1]) for row in rows], int(total or 0)

    async def counts(self, user_id: uuid.UUID) -> dict[UserVacancyStatus, int]:
        rows = await self._session.execute(
            select(UserVacancy.status, func.count())
            .where(UserVacancy.user_id == user_id)
            .group_by(UserVacancy.status)
        )
        return {status: int(count) for status, count in rows.all()}
