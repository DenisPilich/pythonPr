"""Source-agnostic DTOs exchanged between collectors, normalization and ingestion.

Collectors own the mapping from a vendor payload to `CollectedVacancy`; everything
downstream sees only these structures. `RawVacancy` deliberately does not exist:
each adapter already knows how to read its own JSON, so a second intermediate
shape would add a layer without adding meaning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.domain.enums import SalaryPeriod, SeniorityLevel, VacancyLanguage, WorkFormat


@dataclass(frozen=True, slots=True)
class SalaryInput:
    """Salary as stated by the source, before normalization."""

    min: int | None = None
    max: int | None = None
    currency: str | None = None
    period: SalaryPeriod = SalaryPeriod.UNKNOWN
    is_estimated: bool = False


@dataclass(frozen=True, slots=True)
class CollectedVacancy:
    """What a collector yields — vendor-neutral, but not yet cleaned."""

    source_code: str
    external_id: str
    url: str
    title: str
    company_name: str
    description: str
    published_at: datetime | None = None
    location_raw: str | None = None
    work_format_hint: WorkFormat | None = None
    salary: SalaryInput | None = None
    salary_text: str | None = None
    employment_type: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class NormalizedSalary:
    min: int | None
    max: int | None
    currency: str | None
    period: SalaryPeriod
    is_estimated: bool
    monthly_eur: Decimal | None


@dataclass(frozen=True, slots=True)
class TechnologyMention:
    slug: str
    is_required: bool
    mentions: int


@dataclass(frozen=True, slots=True)
class NormalizedVacancy:
    """Ready-to-persist vacancy: cleaned, classified, fingerprinted."""

    source_code: str
    external_id: str
    url: str
    title: str
    company_name: str
    company_key: str
    description_raw: str
    description_clean: str
    location_raw: str | None
    city: str | None
    country_code: str | None
    work_format: WorkFormat
    seniority: SeniorityLevel
    language: VacancyLanguage
    salary: NormalizedSalary | None
    published_at: datetime | None
    technologies: tuple[TechnologyMention, ...]
    fingerprint: str
    content_hash: str
    employment_type: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)
