"""Dashboard statistics schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class VacancyTotals(BaseModel):
    total: int
    active: int
    with_salary: int
    new_last_7_days: int
    remote: int
    remote_share: float = Field(ge=0, le=1)


class DistributionItem(BaseModel):
    key: str
    count: int
    share: float = Field(ge=0, le=1)


class TechnologyStat(BaseModel):
    slug: str
    name: str
    count: int
    share: float = Field(ge=0, le=1)


class CompanyStat(BaseModel):
    id: uuid.UUID
    name: str
    count: int


class SourceStat(BaseModel):
    code: str
    name: str
    is_enabled: bool
    vacancies: int
    last_success_at: datetime | None
    last_run_status: str | None


class AnalysisSummary(BaseModel):
    analyses: int
    average_match_score: float | None


class CollectorRunsSummary(BaseModel):
    last_24h: int
    failed_last_24h: int
    last_status: str | None


class StatsResponse(BaseModel):
    generated_at: datetime
    vacancies: VacancyTotals
    sources: list[SourceStat]
    top_technologies: list[TechnologyStat]
    top_companies: list[CompanyStat]
    seniority: list[DistributionItem]
    work_formats: list[DistributionItem]
    languages: list[DistributionItem]
    analyses: AnalysisSummary
    collector_runs: CollectorRunsSummary
