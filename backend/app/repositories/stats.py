"""Aggregate queries behind `/stats`."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import CollectorRunStatus, WorkFormat
from app.models import (
    AIAnalysis,
    CollectorRun,
    Company,
    Source,
    Technology,
    Vacancy,
    VacancySource,
    VacancyTechnology,
)


@dataclass(frozen=True, slots=True)
class VacancyTotalsRow:
    total: int
    active: int
    with_salary: int
    new_last_7_days: int
    remote: int


@dataclass(frozen=True, slots=True)
class NamedCount:
    key: str
    count: int


@dataclass(frozen=True, slots=True)
class TechnologyCount:
    slug: str
    name: str
    count: int


@dataclass(frozen=True, slots=True)
class CompanyCount:
    id: uuid.UUID
    name: str
    count: int


@dataclass(frozen=True, slots=True)
class SourceHealthRow:
    code: str
    name: str
    is_enabled: bool
    vacancies: int
    last_success_at: datetime | None
    last_run_status: str | None


@dataclass(frozen=True, slots=True)
class AnalysisSummaryRow:
    analyses: int
    average_score: float | None


@dataclass(frozen=True, slots=True)
class RunSummaryRow:
    last_24h: int
    failed_last_24h: int
    last_status: str | None


class StatsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def vacancy_totals(self) -> VacancyTotalsRow:
        since = datetime.now(UTC) - timedelta(days=7)
        row = (
            await self._session.execute(
                select(
                    func.count(Vacancy.id),
                    func.count().filter(Vacancy.is_active.is_(True)),
                    func.count().filter(Vacancy.salary_monthly_eur.is_not(None)),
                    func.count().filter(Vacancy.first_seen_at >= since),
                    func.count().filter(Vacancy.work_format == WorkFormat.REMOTE),
                ).select_from(Vacancy)
            )
        ).one()
        total, active, with_salary, new_last_7_days, remote = (int(value or 0) for value in row)
        return VacancyTotalsRow(
            total=total,
            active=active,
            with_salary=with_salary,
            new_last_7_days=new_last_7_days,
            remote=remote,
        )

    async def distribution(self, column: Any) -> list[NamedCount]:
        count_column = func.count().label("count")
        rows = await self._session.execute(
            select(column, count_column).group_by(column).order_by(count_column.desc())
        )
        result: list[NamedCount] = []
        for value, count in rows.all():
            key = value.value if isinstance(value, StrEnum) else str(value)
            result.append(NamedCount(key=str(key), count=int(count)))
        return result

    async def top_technologies(self, limit: int = 10) -> list[TechnologyCount]:
        count_column = func.count(VacancyTechnology.vacancy_id).label("count")
        rows = await self._session.execute(
            select(Technology.slug, Technology.name, count_column)
            .join(VacancyTechnology, VacancyTechnology.technology_id == Technology.id)
            .group_by(Technology.id)
            .order_by(count_column.desc(), Technology.name.asc())
            .limit(limit)
        )
        return [
            TechnologyCount(slug=slug, name=name, count=int(count))
            for slug, name, count in rows.all()
        ]

    async def top_companies(self, limit: int = 10) -> list[CompanyCount]:
        count_column = func.count(Vacancy.id).label("count")
        rows = await self._session.execute(
            select(Company.id, Company.name, count_column)
            .join(Vacancy, Vacancy.company_id == Company.id)
            .group_by(Company.id)
            .order_by(count_column.desc(), Company.name.asc())
            .limit(limit)
        )
        return [
            CompanyCount(id=company_id, name=name, count=int(count))
            for company_id, name, count in rows.all()
        ]

    async def sources_health(self) -> list[SourceHealthRow]:
        ranked = (
            select(
                CollectorRun.source_id.label("source_id"),
                CollectorRun.status.label("status"),
                func.row_number()
                .over(
                    partition_by=CollectorRun.source_id,
                    order_by=CollectorRun.started_at.desc(),
                )
                .label("rn"),
            )
        ).subquery()
        latest = select(ranked.c.source_id, ranked.c.status).where(ranked.c.rn == 1).subquery()
        rows = await self._session.execute(
            select(
                Source.code,
                Source.name,
                Source.is_enabled,
                func.count(VacancySource.vacancy_id),
                Source.last_success_at,
                latest.c.status,
            )
            .outerjoin(VacancySource, VacancySource.source_id == Source.id)
            .outerjoin(latest, latest.c.source_id == Source.id)
            .group_by(Source.id, latest.c.status)
            .order_by(Source.code)
        )
        return [
            SourceHealthRow(
                code=code,
                name=name,
                is_enabled=bool(enabled),
                vacancies=int(vacancies or 0),
                last_success_at=last_success_at,
                last_run_status=status.value if status is not None else None,
            )
            for code, name, enabled, vacancies, last_success_at, status in rows.all()
        ]

    async def analysis_summary(self) -> AnalysisSummaryRow:
        row = (
            await self._session.execute(
                select(func.count(AIAnalysis.id), func.avg(AIAnalysis.match_score))
            )
        ).one()
        analyses, average = row
        return AnalysisSummaryRow(
            analyses=int(analyses or 0),
            average_score=round(float(average), 1) if average is not None else None,
        )

    async def run_summary(self) -> RunSummaryRow:
        since = datetime.now(UTC) - timedelta(hours=24)
        row = (
            await self._session.execute(
                select(
                    func.count(CollectorRun.id),
                    func.count().filter(CollectorRun.status == CollectorRunStatus.FAILED),
                ).where(CollectorRun.started_at >= since)
            )
        ).one()
        last_status = await self._session.scalar(
            select(CollectorRun.status).order_by(CollectorRun.started_at.desc()).limit(1)
        )
        return RunSummaryRow(
            last_24h=int(row[0] or 0),
            failed_last_24h=int(row[1] or 0),
            last_status=last_status.value if last_status is not None else None,
        )
