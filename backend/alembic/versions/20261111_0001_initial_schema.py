"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-11-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# --- native enum types -----------------------------------------------------
ENUMS: dict[str, tuple[str, ...]] = {
    "work_format": ("remote", "hybrid", "office", "unknown"),
    "seniority_level": ("intern", "junior", "middle", "senior", "lead", "unknown"),
    "salary_period": ("hour", "day", "month", "year", "unknown"),
    "vacancy_language": ("en", "ru", "uk", "de", "pl", "es", "other", "unknown"),
    "english_level": ("a1", "a2", "b1", "b2", "c1", "c2", "native", "unknown"),
    "technology_category": (
        "language",
        "framework",
        "database",
        "devops",
        "cloud",
        "frontend",
        "mobile",
        "testing",
        "messaging",
        "other",
    ),
    "source_kind": ("json_api", "rss", "html"),
    "collector_run_status": ("running", "success", "partial", "failed"),
    "recommendation": ("apply", "consider", "skip"),
    "user_vacancy_status": ("new", "viewed", "saved", "applied", "rejected"),
    "notification_channel": ("telegram",),
    "notification_status": ("pending", "sent", "failed", "skipped"),
}

work_format = postgresql.ENUM(*ENUMS["work_format"], name="work_format", create_type=False)
seniority_level = postgresql.ENUM(
    *ENUMS["seniority_level"], name="seniority_level", create_type=False
)
salary_period = postgresql.ENUM(*ENUMS["salary_period"], name="salary_period", create_type=False)
vacancy_language = postgresql.ENUM(
    *ENUMS["vacancy_language"], name="vacancy_language", create_type=False
)
english_level = postgresql.ENUM(*ENUMS["english_level"], name="english_level", create_type=False)
technology_category = postgresql.ENUM(
    *ENUMS["technology_category"], name="technology_category", create_type=False
)
source_kind = postgresql.ENUM(*ENUMS["source_kind"], name="source_kind", create_type=False)
collector_run_status = postgresql.ENUM(
    *ENUMS["collector_run_status"], name="collector_run_status", create_type=False
)
recommendation = postgresql.ENUM(*ENUMS["recommendation"], name="recommendation", create_type=False)
user_vacancy_status = postgresql.ENUM(
    *ENUMS["user_vacancy_status"], name="user_vacancy_status", create_type=False
)
notification_channel = postgresql.ENUM(
    *ENUMS["notification_channel"], name="notification_channel", create_type=False
)
notification_status = postgresql.ENUM(
    *ENUMS["notification_status"], name="notification_status", create_type=False
)

SEARCH_VECTOR_EXPRESSION = (
    "setweight(to_tsvector('simple', coalesce(title, '')), 'A') || "
    "setweight(to_tsvector('simple', coalesce(description_clean, '')), 'B')"
)


def upgrade() -> None:
    for name, values in ENUMS.items():
        literals = ", ".join(f"'{value}'" for value in values)
        op.execute(f"CREATE TYPE {name} AS ENUM ({literals})")

    # --- users -------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("first_name", sa.String(length=128), nullable=True),
        sa.Column(
            "timezone", sa.String(length=64), server_default=sa.text("'UTC'"), nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("telegram_id", name="uq_users_telegram_id"),
    )

    # --- user_profiles -----------------------------------------------------
    op.create_table(
        "user_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("headline", sa.String(length=160), nullable=True),
        sa.Column(
            "desired_positions",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column(
            "target_seniority",
            postgresql.ARRAY(seniority_level),
            server_default=sa.text("'{}'::seniority_level[]"),
            nullable=False,
        ),
        sa.Column(
            "skills",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column(
            "preferred_stack",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column(
            "excluded_stack",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column(
            "english_level",
            english_level,
            server_default=sa.text("'unknown'"),
            nullable=False,
        ),
        sa.Column("min_salary_amount", sa.Integer(), nullable=True),
        sa.Column(
            "salary_currency",
            sa.String(length=3),
            server_default=sa.text("'EUR'"),
            nullable=False,
        ),
        sa.Column(
            "preferred_locations",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column(
            "work_formats",
            postgresql.ARRAY(work_format),
            server_default=sa.text("'{}'::work_format[]"),
            nullable=False,
        ),
        sa.Column(
            "min_match_score", sa.SmallInteger(), server_default=sa.text("70"), nullable=False
        ),
        sa.Column(
            "notifications_enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "max_notifications_per_day",
            sa.SmallInteger(),
            server_default=sa.text("10"),
            nullable=False,
        ),
        sa.Column("profile_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "min_salary_amount IS NULL OR min_salary_amount >= 0",
            name="ck_user_profiles_salary_non_negative",
        ),
        sa.CheckConstraint(
            "min_match_score BETWEEN 0 AND 100", name="ck_user_profiles_match_score_range"
        ),
        sa.CheckConstraint(
            "max_notifications_per_day BETWEEN 0 AND 100",
            name="ck_user_profiles_daily_quota_range",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_profiles_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_profiles"),
        sa.UniqueConstraint("user_id", name="uq_user_profiles_user_id"),
    )

    # --- sources -----------------------------------------------------------
    op.create_table(
        "sources",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("kind", source_kind, nullable=False),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "rate_limit_per_min",
            sa.SmallInteger(),
            server_default=sa.text("30"),
            nullable=False,
        ),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sources"),
        sa.UniqueConstraint("code", name="uq_sources_code"),
    )

    # --- companies ---------------------------------------------------------
    op.create_table(
        "companies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("website", sa.Text(), nullable=True),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_companies"),
        sa.UniqueConstraint("normalized_name", name="uq_companies_normalized_name"),
    )

    # --- technologies ------------------------------------------------------
    op.create_table(
        "technologies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column(
            "category",
            technology_category,
            server_default=sa.text("'other'"),
            nullable=False,
        ),
        sa.Column(
            "aliases",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_technologies"),
        sa.UniqueConstraint("slug", name="uq_technologies_slug"),
    )

    # --- vacancies ---------------------------------------------------------
    op.create_table(
        "vacancies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description_raw", sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column("description_clean", sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(length=3), nullable=True),
        sa.Column(
            "salary_period",
            salary_period,
            server_default=sa.text("'unknown'"),
            nullable=False,
        ),
        sa.Column(
            "salary_is_estimated",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("salary_monthly_eur", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("location_raw", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=True),
        sa.Column(
            "work_format",
            work_format,
            server_default=sa.text("'unknown'"),
            nullable=False,
        ),
        sa.Column(
            "seniority",
            seniority_level,
            server_default=sa.text("'unknown'"),
            nullable=False,
        ),
        sa.Column(
            "language",
            vacancy_language,
            server_default=sa.text("'unknown'"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "fingerprint_version",
            sa.SmallInteger(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(SEARCH_VECTOR_EXPRESSION, persisted=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "salary_min IS NULL OR salary_min >= 0",
            name="ck_vacancies_salary_min_non_negative",
        ),
        sa.CheckConstraint(
            "salary_max IS NULL OR salary_max >= 0",
            name="ck_vacancies_salary_max_non_negative",
        ),
        sa.CheckConstraint(
            "salary_max IS NULL OR salary_min IS NULL OR salary_max >= salary_min",
            name="ck_vacancies_salary_range_order",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_vacancies_company_id_companies",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_vacancies"),
        sa.UniqueConstraint("fingerprint", name="uq_vacancies_fingerprint"),
    )
    op.create_index("ix_vacancies_company_published", "vacancies", ["company_id", "published_at"])
    op.create_index("ix_vacancies_seniority_work_format", "vacancies", ["seniority", "work_format"])
    op.create_index("ix_vacancies_published_at", "vacancies", ["published_at"])
    op.create_index("ix_vacancies_last_seen_at", "vacancies", ["last_seen_at"])
    op.create_index(
        "ix_vacancies_search_vector",
        "vacancies",
        ["search_vector"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_vacancies_active_published",
        "vacancies",
        ["published_at"],
        postgresql_where=sa.text("is_active"),
    )

    # --- vacancy_sources ---------------------------------------------------
    op.create_table(
        "vacancy_sources",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("vacancy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            name="fk_vacancy_sources_source_id_sources",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["vacancy_id"],
            ["vacancies.id"],
            name="fk_vacancy_sources_vacancy_id_vacancies",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_vacancy_sources"),
        sa.UniqueConstraint(
            "source_id",
            "external_id",
            name="uq_vacancy_sources_source_id_external_id",
        ),
    )
    op.create_index("ix_vacancy_sources_vacancy_id", "vacancy_sources", ["vacancy_id"])

    # --- vacancy_technologies ---------------------------------------------
    op.create_table(
        "vacancy_technologies",
        sa.Column("vacancy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("technology_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "is_required",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("mentions", sa.SmallInteger(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint("mentions >= 1", name="ck_vacancy_technologies_mentions_positive"),
        sa.ForeignKeyConstraint(
            ["technology_id"],
            ["technologies.id"],
            name="fk_vacancy_technologies_technology_id_technologies",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["vacancy_id"],
            ["vacancies.id"],
            name="fk_vacancy_technologies_vacancy_id_vacancies",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("vacancy_id", "technology_id", name="pk_vacancy_technologies"),
    )
    op.create_index(
        "ix_vacancy_technologies_technology_id",
        "vacancy_technologies",
        ["technology_id"],
    )

    # --- ai_analyses -------------------------------------------------------
    op.create_table(
        "ai_analyses",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("vacancy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_hash", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=16), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("match_score", sa.SmallInteger(), nullable=False),
        sa.Column("experience_match", sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column("skills_match", sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column(
            "missing_skills",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column(
            "strong_matches",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column(
            "red_flags",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column("recommendation", recommendation, nullable=False),
        sa.Column("reason", sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column(
            "is_degraded",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("prompt_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "cost_usd",
            sa.Numeric(precision=10, scale=6),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("latency_ms", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("raw_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "match_score BETWEEN 0 AND 100", name="ck_ai_analyses_match_score_range"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_ai_analyses_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["vacancy_id"],
            ["vacancies.id"],
            name="fk_ai_analyses_vacancy_id_vacancies",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ai_analyses"),
        sa.UniqueConstraint(
            "vacancy_id",
            "user_id",
            "profile_hash",
            "prompt_version",
            name="uq_ai_analyses_vacancy_user_profile_prompt",
        ),
    )
    op.create_index("ix_ai_analyses_user_created", "ai_analyses", ["user_id", "created_at"])

    # --- user_vacancies ----------------------------------------------------
    op.create_table(
        "user_vacancies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vacancy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ai_analysis_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            user_vacancy_status,
            server_default=sa.text("'new'"),
            nullable=False,
        ),
        sa.Column("match_score", sa.SmallInteger(), nullable=True),
        sa.Column(
            "is_notified",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "match_score IS NULL OR match_score BETWEEN 0 AND 100",
            name="ck_user_vacancies_match_score_range",
        ),
        sa.ForeignKeyConstraint(
            ["ai_analysis_id"],
            ["ai_analyses.id"],
            name="fk_user_vacancies_ai_analysis_id_ai_analyses",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_vacancies_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["vacancy_id"],
            ["vacancies.id"],
            name="fk_user_vacancies_vacancy_id_vacancies",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_vacancies"),
        sa.UniqueConstraint("user_id", "vacancy_id", name="uq_user_vacancies_user_id_vacancy_id"),
    )
    op.create_index(
        "ix_user_vacancies_user_status_score",
        "user_vacancies",
        ["user_id", "status", "match_score"],
    )
    op.create_index("ix_user_vacancies_vacancy_id", "user_vacancies", ["vacancy_id"])

    # --- notifications -----------------------------------------------------
    op.create_table(
        "notifications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vacancy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "channel",
            notification_channel,
            server_default=sa.text("'telegram'"),
            nullable=False,
        ),
        sa.Column(
            "status",
            notification_status,
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_notifications_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["vacancy_id"],
            ["vacancies.id"],
            name="fk_notifications_vacancy_id_vacancies",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_notifications"),
        sa.UniqueConstraint(
            "user_id", "vacancy_id", "channel", name="uq_notifications_user_id_vacancy_id_channel"
        ),
    )
    op.create_index(
        "ix_notifications_pending",
        "notifications",
        ["status", "created_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )

    # --- collector_runs ----------------------------------------------------
    op.create_table(
        "collector_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("celery_task_id", sa.String(length=64), nullable=True),
        sa.Column(
            "status",
            collector_run_status,
            server_default=sa.text("'running'"),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("items_fetched", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("items_created", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("items_updated", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("items_skipped", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            name="fk_collector_runs_source_id_sources",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_collector_runs"),
    )
    op.create_index(
        "ix_collector_runs_source_started", "collector_runs", ["source_id", "started_at"]
    )


def downgrade() -> None:
    op.drop_table("collector_runs")
    op.drop_table("notifications")
    op.drop_table("user_vacancies")
    op.drop_table("ai_analyses")
    op.drop_table("vacancy_technologies")
    op.drop_table("vacancy_sources")
    op.drop_table("vacancies")
    op.drop_table("technologies")
    op.drop_table("companies")
    op.drop_table("sources")
    op.drop_table("user_profiles")
    op.drop_table("users")

    for name in reversed(ENUMS):
        op.execute(f"DROP TYPE {name}")
