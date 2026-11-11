"""Company and technology catalogs with demand counts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import TechnologyCategory
from app.models import Company, Technology, Vacancy, VacancyTechnology


@dataclass(frozen=True, slots=True)
class CompanyRow:
    company: Company
    vacancy_count: int


@dataclass(frozen=True, slots=True)
class TechnologyRow:
    technology: Technology
    vacancy_count: int


class CompanyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_companies(
        self,
        *,
        q: str | None = None,
        sort_by_vacancies: bool = True,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[CompanyRow], int]:
        count_statement = select(func.count(Company.id))
        statement = (
            select(Company, func.count(Vacancy.id).label("vacancy_count"))
            .outerjoin(Vacancy, Vacancy.company_id == Company.id)
            .group_by(Company.id)
        )
        if q:
            pattern = f"%{q.strip().lower()}%"
            count_statement = count_statement.where(Company.normalized_name.ilike(pattern))
            statement = statement.where(Company.normalized_name.ilike(pattern))

        total = await self._session.scalar(count_statement) or 0
        order = func.count(Vacancy.id).desc() if sort_by_vacancies else Company.name.asc()
        rows = await self._session.execute(
            statement.order_by(order, Company.name.asc()).limit(limit).offset(offset)
        )
        items = [
            CompanyRow(company=company, vacancy_count=int(count)) for company, count in rows.all()
        ]
        return items, total


class TechnologyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_technologies(
        self,
        *,
        q: str | None = None,
        category: TechnologyCategory | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[TechnologyRow], int]:
        conditions: list[Any] = []
        if q:
            conditions.append(Technology.name.ilike(f"%{q.strip()}%"))
        if category is not None:
            conditions.append(Technology.category == category)

        total = (
            await self._session.scalar(select(func.count(Technology.id)).where(*conditions)) or 0
        )
        count_column = func.count(VacancyTechnology.vacancy_id)
        rows = await self._session.execute(
            select(Technology, count_column.label("vacancy_count"))
            .outerjoin(VacancyTechnology, VacancyTechnology.technology_id == Technology.id)
            .where(*conditions)
            .group_by(Technology.id)
            .order_by(count_column.desc(), Technology.name.asc())
            .limit(limit)
            .offset(offset)
        )
        items = [
            TechnologyRow(technology=technology, vacancy_count=int(count))
            for technology, count in rows.all()
        ]
        return items, total
