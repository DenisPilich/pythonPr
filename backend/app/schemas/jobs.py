"""Job schemas — list, detail and the nested company/technology/source views."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    SalaryPeriod,
    SeniorityLevel,
    TechnologyCategory,
    VacancyLanguage,
    WorkFormat,
)


class CompanyBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    normalized_name: str
    website: str | None = None
    logo_url: str | None = None


class TechnologyBrief(BaseModel):
    slug: str
    name: str
    category: TechnologyCategory


class SourceRef(BaseModel):
    source: str = Field(description="Source code, e.g. `hh`")
    name: str
    url: str


class JobListItem(BaseModel):
    id: uuid.UUID
    title: str
    company: CompanyBrief
    url: str = Field(description="Canonical apply URL (first source that delivered the vacancy)")
    location_raw: str | None
    city: str | None
    country_code: str | None
    work_format: WorkFormat
    seniority: SeniorityLevel
    language: VacancyLanguage
    salary_min: int | None
    salary_max: int | None
    salary_currency: str | None
    salary_period: SalaryPeriod
    salary_monthly_eur: Decimal | None = Field(
        None, description="Normalized monthly gross approximation in EUR"
    )
    published_at: datetime | None
    first_seen_at: datetime
    technologies: list[TechnologyBrief]
    sources: list[SourceRef]


class JobDetail(JobListItem):
    description: str = Field(description="Plain-text description used for matching")
    created_at: datetime
    updated_at: datetime


class JobListResponse(BaseModel):
    """Documentation-only wrapper; the endpoint returns `Page[JobListItem]`."""

    items: list[JobListItem]
    total: int
    limit: int
    offset: int


JOB_LIST_EXAMPLE: dict[str, Any] = {
    "items": [
        {
            "id": "0f8f7f2e-6a4b-4f0e-9b6a-0d4e2b1c3a55",
            "title": "Senior Python Developer",
            "company": {
                "id": "5c1d9a2b-3f4e-4a6b-8c7d-9e0f1a2b3c4d",
                "name": "Acme",
                "normalized_name": "acme",
                "website": None,
                "logo_url": None,
            },
            "url": "https://hh.ru/vacancy/123",
            "location_raw": "Remote",
            "city": None,
            "country_code": None,
            "work_format": "remote",
            "seniority": "senior",
            "language": "en",
            "salary_min": 60000,
            "salary_max": 80000,
            "salary_currency": "EUR",
            "salary_period": "year",
            "salary_monthly_eur": "5366.67",
            "published_at": "2026-11-01T10:00:00Z",
            "first_seen_at": "2026-11-01T10:05:00Z",
            "technologies": [{"slug": "python", "name": "Python", "category": "language"}],
            "sources": [{"source": "hh", "name": "hh.ru", "url": "https://hh.ru/vacancy/123"}],
        }
    ],
    "total": 1,
    "limit": 20,
    "offset": 0,
}
