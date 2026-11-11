"""Job search queries: filtering, sorting, pagination.

Filters are expressed as subqueries on `vacancy_id` rather than joins, which keeps
the count query and the page query structurally identical and avoids `DISTINCT`
on a wide row.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.enums import SeniorityLevel, VacancyLanguage, WorkFormat
from app.models import (
    Company,
    Source,
    Technology,
    Vacancy,
    VacancySource,
    VacancyTechnology,
)
from app.schemas.common import JobSortField


@dataclass(frozen=True, slots=True)
class JobFilters:
    q: str | None = None
    source: str | None = None
    company: str | None = None
    technologies: tuple[str, ...] = ()
    seniority: tuple[SeniorityLevel, ...] = ()
    work_formats: tuple[WorkFormat, ...] = ()
    languages: tuple[VacancyLanguage, ...] = ()
    min_salary_eur: Decimal | None = None
    max_salary_eur: Decimal | None = None
    published_after: datetime | None = None
    published_before: datetime | None = None
    include_inactive: bool = False


@dataclass(frozen=True, slots=True)
class JobPage:
    items: list[Vacancy] = field(default_factory=list)
    total: int = 0


def job_load_options() -> list[Any]:
    return [
        selectinload(Vacancy.company),
        selectinload(Vacancy.sources).selectinload(VacancySource.source),
        selectinload(Vacancy.technologies).selectinload(VacancyTechnology.technology),
    ]


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _conditions(self, filters: JobFilters) -> list[Any]:
        conditions: list[Any] = []
        if filters.q:
            term = filters.q.strip()
            conditions.append(
                or_(
                    Vacancy.search_vector.op("@@")(func.plainto_tsquery("simple", term)),
                    Vacancy.title.ilike(f"%{term}%"),
                )
            )
        if filters.source:
            conditions.append(
                Vacancy.id.in_(
                    select(VacancySource.vacancy_id)
                    .join(Source, Source.id == VacancySource.source_id)
                    .where(Source.code == filters.source)
                )
            )
        if filters.technologies:
            conditions.append(
                Vacancy.id.in_(
                    select(VacancyTechnology.vacancy_id)
                    .join(Technology, Technology.id == VacancyTechnology.technology_id)
                    .where(Technology.slug.in_(filters.technologies))
                )
            )
        if filters.company:
            conditions.append(
                Vacancy.company_id.in_(
                    select(Company.id).where(
                        Company.normalized_name.ilike(f"%{filters.company.lower()}%")
                    )
                )
            )
        if filters.seniority:
            conditions.append(Vacancy.seniority.in_(filters.seniority))
        if filters.work_formats:
            conditions.append(Vacancy.work_format.in_(filters.work_formats))
        if filters.languages:
            conditions.append(Vacancy.language.in_(filters.languages))
        if filters.min_salary_eur is not None:
            conditions.append(Vacancy.salary_monthly_eur >= filters.min_salary_eur)
        if filters.max_salary_eur is not None:
            conditions.append(Vacancy.salary_monthly_eur <= filters.max_salary_eur)
        if filters.published_after is not None:
            conditions.append(Vacancy.published_at >= filters.published_after)
        if filters.published_before is not None:
            conditions.append(Vacancy.published_at <= filters.published_before)
        if not filters.include_inactive:
            conditions.append(Vacancy.is_active.is_(True))
        return conditions

    @staticmethod
    def _order_by(sort: JobSortField, descending: bool) -> Any:
        columns = {
            JobSortField.PUBLISHED_AT: Vacancy.published_at,
            JobSortField.CREATED_AT: Vacancy.created_at,
            JobSortField.SALARY: Vacancy.salary_monthly_eur,
            JobSortField.TITLE: Vacancy.title,
        }
        column = columns[sort]
        return column.desc() if descending else column.asc()

    async def list_jobs(
        self,
        filters: JobFilters,
        *,
        sort: JobSortField = JobSortField.PUBLISHED_AT,
        descending: bool = True,
        limit: int = 20,
        offset: int = 0,
    ) -> JobPage:
        conditions = self._conditions(filters)

        total = await self._session.scalar(
            select(func.count()).select_from(Vacancy).where(*conditions)
        )
        statement = (
            select(Vacancy)
            .where(*conditions)
            .options(*job_load_options())
            .order_by(self._order_by(sort, descending).nulls_last(), Vacancy.id.desc())
            .limit(limit)
            .offset(offset)
        )
        items = list((await self._session.scalars(statement)).all())
        return JobPage(items=items, total=total or 0)

    async def get_job(self, job_id: uuid.UUID) -> Vacancy | None:
        return await self._session.scalar(
            select(Vacancy).where(Vacancy.id == job_id).options(*job_load_options())
        )
