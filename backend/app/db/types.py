"""Reusable PostgreSQL-native column types built from domain enums.

The instances are module-level on purpose: one `Enum` object per PostgreSQL type
means SQLAlchemy emits `CREATE TYPE` once, and every column and array shares it.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Enum as SAEnum

from app.domain.enums import (
    CollectorRunStatus,
    EnglishLevel,
    NotificationChannel,
    NotificationStatus,
    Recommendation,
    SalaryPeriod,
    SeniorityLevel,
    SourceKind,
    TechnologyCategory,
    UserVacancyStatus,
    VacancyLanguage,
    WorkFormat,
)


def pg_enum(enum_cls: type[Any], name: str) -> SAEnum[Any]:
    """Native PostgreSQL enum that stores member *values*, not names."""
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=True,
        create_constraint=False,
        validate_strings=True,
        values_callable=lambda member_cls: [member.value for member in member_cls],
    )


work_format_type = pg_enum(WorkFormat, "work_format")
seniority_level_type = pg_enum(SeniorityLevel, "seniority_level")
salary_period_type = pg_enum(SalaryPeriod, "salary_period")
vacancy_language_type = pg_enum(VacancyLanguage, "vacancy_language")
english_level_type = pg_enum(EnglishLevel, "english_level")
technology_category_type = pg_enum(TechnologyCategory, "technology_category")
source_kind_type = pg_enum(SourceKind, "source_kind")
collector_run_status_type = pg_enum(CollectorRunStatus, "collector_run_status")
recommendation_type = pg_enum(Recommendation, "recommendation")
user_vacancy_status_type = pg_enum(UserVacancyStatus, "user_vacancy_status")
notification_channel_type = pg_enum(NotificationChannel, "notification_channel")
notification_status_type = pg_enum(NotificationStatus, "notification_status")
