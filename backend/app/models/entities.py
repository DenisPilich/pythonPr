"""ORM entities.

All models live in one module on purpose: they form a single aggregate graph with
mutual relationships, and splitting them forces cross-module forward references
that SQLAlchemy resolves at mapper-configuration time. One module keeps the
mapping obvious and import order irrelevant.

Rules: models contain mapping only — no queries, no business logic, no I/O.
Every relationship is `lazy="raise"`, so an accidental lazy load in async code
fails loudly instead of raising `MissingGreenlet` somewhere deep in a serializer.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import (
    collector_run_status_type,
    english_level_type,
    notification_channel_type,
    notification_status_type,
    recommendation_type,
    salary_period_type,
    seniority_level_type,
    source_kind_type,
    technology_category_type,
    user_vacancy_status_type,
    vacancy_language_type,
    work_format_type,
)
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


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(128))
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="UTC", server_default=text("'UTC'")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    profile: Mapped[UserProfile | None] = relationship(
        back_populates="user", uselist=False, lazy="raise", cascade="all, delete-orphan", passive_deletes=True
    )
    vacancies: Mapped[list[UserVacancy]] = relationship(
        back_populates="user", lazy="raise", cascade="all, delete-orphan", passive_deletes=True
    )
    analyses: Mapped[list[AIAnalysis]] = relationship(
        back_populates="user", lazy="raise", cascade="all, delete-orphan", passive_deletes=True
    )
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="user", lazy="raise", cascade="all, delete-orphan", passive_deletes=True
    )


class UserProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_profiles"
    __table_args__ = (
        CheckConstraint(
            "min_salary_amount IS NULL OR min_salary_amount >= 0",
            name="salary_non_negative",
        ),
        CheckConstraint("min_match_score BETWEEN 0 AND 100", name="match_score_range"),
        CheckConstraint(
            "max_notifications_per_day BETWEEN 0 AND 100", name="daily_quota_range"
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    headline: Mapped[str | None] = mapped_column(String(160))
    desired_positions: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default=text("'{}'::text[]")
    )
    target_seniority: Mapped[list[SeniorityLevel]] = mapped_column(
        ARRAY(seniority_level_type),
        nullable=False,
        default=list,
        server_default=text("'{}'::seniority_level[]"),
    )
    skills: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default=text("'{}'::text[]")
    )
    preferred_stack: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default=text("'{}'::text[]")
    )
    excluded_stack: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default=text("'{}'::text[]")
    )
    english_level: Mapped[EnglishLevel] = mapped_column(
        english_level_type,
        nullable=False,
        default=EnglishLevel.UNKNOWN,
        server_default=text("'unknown'"),
    )
    min_salary_amount: Mapped[int | None] = mapped_column(Integer)
    salary_currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="EUR", server_default=text("'EUR'")
    )
    preferred_locations: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default=text("'{}'::text[]")
    )
    work_formats: Mapped[list[WorkFormat]] = mapped_column(
        ARRAY(work_format_type),
        nullable=False,
        default=list,
        server_default=text("'{}'::work_format[]"),
    )
    min_match_score: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=70, server_default=text("70")
    )
    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    max_notifications_per_day: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=10, server_default=text("10")
    )
    profile_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    user: Mapped[User] = relationship(back_populates="profile", lazy="raise")


class Source(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sources"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    kind: Mapped[SourceKind] = mapped_column(source_kind_type, nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text)
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    rate_limit_per_min: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=30, server_default=text("30")
    )
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    vacancy_sources: Mapped[list[VacancySource]] = relationship(
        back_populates="source", lazy="raise"
    )
    runs: Mapped[list[CollectorRun]] = relationship(
        back_populates="source", lazy="raise", cascade="all, delete-orphan", passive_deletes=True
    )


class Company(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    website: Mapped[str | None] = mapped_column(Text)
    logo_url: Mapped[str | None] = mapped_column(Text)

    vacancies: Mapped[list[Vacancy]] = relationship(back_populates="company", lazy="raise")


class Vacancy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "vacancies"
    __table_args__ = (
        CheckConstraint(
            "salary_min IS NULL OR salary_min >= 0", name="salary_min_non_negative"
        ),
        CheckConstraint(
            "salary_max IS NULL OR salary_max >= 0", name="salary_max_non_negative"
        ),
        CheckConstraint(
            "salary_max IS NULL OR salary_min IS NULL OR salary_max >= salary_min",
            name="salary_range_order",
        ),
        Index("ix_vacancies_company_published", "company_id", "published_at"),
        Index("ix_vacancies_seniority_work_format", "seniority", "work_format"),
        Index("ix_vacancies_published_at", "published_at"),
        Index("ix_vacancies_last_seen_at", "last_seen_at"),
        Index("ix_vacancies_search_vector", "search_vector", postgresql_using="gin"),
        Index(
            "ix_vacancies_active_published",
            "published_at",
            postgresql_where=text("is_active"),
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description_raw: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=text("''")
    )
    description_clean: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=text("''")
    )
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    salary_currency: Mapped[str | None] = mapped_column(String(3))
    salary_period: Mapped[SalaryPeriod] = mapped_column(
        salary_period_type,
        nullable=False,
        default=SalaryPeriod.UNKNOWN,
        server_default=text("'unknown'"),
    )
    salary_is_estimated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    salary_monthly_eur: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    location_raw: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(128))
    country_code: Mapped[str | None] = mapped_column(String(2))
    work_format: Mapped[WorkFormat] = mapped_column(
        work_format_type,
        nullable=False,
        default=WorkFormat.UNKNOWN,
        server_default=text("'unknown'"),
    )
    seniority: Mapped[SeniorityLevel] = mapped_column(
        seniority_level_type,
        nullable=False,
        default=SeniorityLevel.UNKNOWN,
        server_default=text("'unknown'"),
    )
    language: Mapped[VacancyLanguage] = mapped_column(
        vacancy_language_type,
        nullable=False,
        default=VacancyLanguage.UNKNOWN,
        server_default=text("'unknown'"),
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    fingerprint_version: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1, server_default=text("1")
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('simple', coalesce(title, '')), 'A') || "
            "setweight(to_tsvector('simple', coalesce(description_clean, '')), 'B')",
            persisted=True,
        ),
    )

    company: Mapped[Company] = relationship(back_populates="vacancies", lazy="raise")
    sources: Mapped[list[VacancySource]] = relationship(
        back_populates="vacancy", lazy="raise", cascade="all, delete-orphan", passive_deletes=True
    )
    technologies: Mapped[list[VacancyTechnology]] = relationship(
        back_populates="vacancy", lazy="raise", cascade="all, delete-orphan", passive_deletes=True
    )
    analyses: Mapped[list[AIAnalysis]] = relationship(
        back_populates="vacancy", lazy="raise", cascade="all, delete-orphan", passive_deletes=True
    )
    user_vacancies: Mapped[list[UserVacancy]] = relationship(
        back_populates="vacancy", lazy="raise", cascade="all, delete-orphan", passive_deletes=True
    )
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="vacancy", lazy="raise", cascade="all, delete-orphan", passive_deletes=True
    )


class VacancySource(UUIDPrimaryKeyMixin, Base):
    """Provenance: which source delivered this vacancy, under which external id."""

    __tablename__ = "vacancy_sources"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id"),
        Index("ix_vacancy_sources_vacancy_id", "vacancy_id"),
    )

    vacancy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vacancies.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    vacancy: Mapped[Vacancy] = relationship(back_populates="sources", lazy="raise")
    source: Mapped[Source] = relationship(back_populates="vacancy_sources", lazy="raise")


class Technology(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "technologies"

    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[TechnologyCategory] = mapped_column(
        technology_category_type,
        nullable=False,
        default=TechnologyCategory.OTHER,
        server_default=text("'other'"),
    )
    aliases: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default=text("'{}'::text[]")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    vacancies: Mapped[list[VacancyTechnology]] = relationship(
        back_populates="technology", lazy="raise"
    )


class VacancyTechnology(Base):
    __tablename__ = "vacancy_technologies"
    __table_args__ = (
        Index("ix_vacancy_technologies_technology_id", "technology_id"),
        CheckConstraint("mentions >= 1", name="mentions_positive"),
    )

    vacancy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vacancies.id", ondelete="CASCADE"),
        primary_key=True,
    )
    technology_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("technologies.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    is_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    mentions: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1, server_default=text("1")
    )

    vacancy: Mapped[Vacancy] = relationship(back_populates="technologies", lazy="raise")
    technology: Mapped[Technology] = relationship(back_populates="vacancies", lazy="raise")


class AIAnalysis(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ai_analyses"
    __table_args__ = (
        UniqueConstraint("vacancy_id", "user_id", "profile_hash", "prompt_version"),
        Index("ix_ai_analyses_user_created", "user_id", "created_at"),
        CheckConstraint("match_score BETWEEN 0 AND 100", name="match_score_range"),
    )

    vacancy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vacancies.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    profile_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(16), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    match_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    experience_match: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=text("''")
    )
    skills_match: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=text("''")
    )
    missing_skills: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default=text("'{}'::text[]")
    )
    strong_matches: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default=text("'{}'::text[]")
    )
    red_flags: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default=text("'{}'::text[]")
    )
    recommendation: Mapped[Recommendation] = mapped_column(
        recommendation_type, nullable=False
    )
    reason: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=text("''")
    )
    is_degraded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    prompt_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, default=Decimal("0"), server_default=text("0")
    )
    latency_ms: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    raw_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    vacancy: Mapped[Vacancy] = relationship(back_populates="analyses", lazy="raise")
    user: Mapped[User] = relationship(back_populates="analyses", lazy="raise")
    user_vacancy: Mapped[UserVacancy | None] = relationship(
        back_populates="ai_analysis", uselist=False, lazy="raise"
    )


class UserVacancy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Per-user state machine and history for one vacancy."""

    __tablename__ = "user_vacancies"
    __table_args__ = (
        UniqueConstraint("user_id", "vacancy_id"),
        Index("ix_user_vacancies_user_status_score", "user_id", "status", "match_score"),
        Index("ix_user_vacancies_vacancy_id", "vacancy_id"),
        CheckConstraint(
            "match_score IS NULL OR match_score BETWEEN 0 AND 100",
            name="match_score_range",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    vacancy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vacancies.id", ondelete="CASCADE"),
        nullable=False,
    )
    ai_analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_analyses.id", ondelete="SET NULL")
    )
    status: Mapped[UserVacancyStatus] = mapped_column(
        user_vacancy_status_type,
        nullable=False,
        default=UserVacancyStatus.NEW,
        server_default=text("'new'"),
    )
    match_score: Mapped[int | None] = mapped_column(SmallInteger)
    is_notified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    saved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="vacancies", lazy="raise")
    vacancy: Mapped[Vacancy] = relationship(back_populates="user_vacancies", lazy="raise")
    ai_analysis: Mapped[AIAnalysis | None] = relationship(
        back_populates="user_vacancy", lazy="raise"
    )


class Notification(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("user_id", "vacancy_id", "channel"),
        Index(
            "ix_notifications_pending",
            "status",
            "created_at",
            postgresql_where=text("status = 'pending'"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    vacancy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vacancies.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        notification_channel_type,
        nullable=False,
        default=NotificationChannel.TELEGRAM,
        server_default=text("'telegram'"),
    )
    status: Mapped[NotificationStatus] = mapped_column(
        notification_status_type,
        nullable=False,
        default=NotificationStatus.PENDING,
        server_default=text("'pending'"),
    )
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger)
    error: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="notifications", lazy="raise")
    vacancy: Mapped[Vacancy] = relationship(back_populates="notifications", lazy="raise")


class CollectorRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "collector_runs"
    __table_args__ = (
        Index("ix_collector_runs_source_started", "source_id", "started_at"),
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    celery_task_id: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[CollectorRunStatus] = mapped_column(
        collector_run_status_type,
        nullable=False,
        default=CollectorRunStatus.RUNNING,
        server_default=text("'running'"),
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    items_fetched: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    items_created: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    items_updated: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    items_skipped: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    error: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)

    source: Mapped[Source] = relationship(back_populates="runs", lazy="raise")
