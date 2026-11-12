"""Typed application settings, loaded once per process from the environment."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal
from urllib.parse import quote_plus

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Single source of truth for configuration.

    Values come from, in order of precedence: explicit arguments, environment
    variables, `.env` in the current directory, `.env` one level up.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- application -----------------------------------------------------
    app_name: str = "AI Job Radar"
    version: str = "0.1.0"
    environment: Literal["local", "test", "staging", "production"] = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_json: bool = True
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"]
    )

    # --- security --------------------------------------------------------
    api_key: SecretStr = SecretStr("dev-secret-change-me")
    telegram_allowed_user_ids: list[int] = Field(default_factory=list)
    demo_telegram_id: int = 100_000_001

    # --- caching ---------------------------------------------------------
    stats_cache_enabled: bool = True

    # --- database --------------------------------------------------------
    database_url: str | None = None
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "radar"
    postgres_password: SecretStr = SecretStr("radar")
    postgres_db: str = "radar"
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 5

    # --- redis -----------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"

    # --- collection / http ----------------------------------------------
    http_timeout_seconds: float = 15.0
    http_max_retries: int = 3
    http_retry_base_seconds: float = 0.5
    http_retry_max_seconds: float = 8.0
    http_max_connections: int = 10
    http_user_agent: str = "AI-Job-Radar/0.1 (+https://github.com/your-handle/ai-job-radar)"
    collector_batch_size: int = 50
    collect_interval_minutes: int = 15
    stale_vacancy_days: int = 60

    # --- scheduling ------------------------------------------------------
    analyze_interval_minutes: int = 5
    notify_interval_minutes: int = 2
    stats_interval_minutes: int = 5
    analysis_lookback_days: int = 14
    notification_batch_size: int = 20

    # --- ai --------------------------------------------------------------
    ai_provider: Literal["mock", "openai"] = "mock"
    openai_api_key: SecretStr | None = None
    openai_base_url: str | None = None
    ai_model: str = "gpt-4o-mini"
    ai_temperature: float = 0.2
    ai_max_analyses_per_run: int = 50
    ai_daily_budget_usd: float = 2.0
    ai_fallback_to_mock: bool = True
    ai_timeout_seconds: float = 60.0
    ai_max_retries: int = 2

    # --- telegram --------------------------------------------------------
    telegram_bot_token: SecretStr | None = None

    @field_validator("api_v1_prefix")
    @classmethod
    def _validate_api_prefix(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("api_v1_prefix must start with '/'")
        if len(value) > 1 and value.endswith("/"):
            raise ValueError("api_v1_prefix must not end with '/'")
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: Any) -> Any:
        if not isinstance(value, str) or not value:
            return None
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @field_validator("openai_api_key", "telegram_bot_token", mode="before")
    @classmethod
    def _blank_secret_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("openai_base_url", mode="before")
    @classmethod
    def _blank_url_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def sqlalchemy_dsn(self) -> str:
        """Async SQLAlchemy DSN, either explicit or built from parts."""
        if self.database_url:
            return self.database_url
        user = quote_plus(self.postgres_user)
        password = quote_plus(self.postgres_password.get_secret_value())
        return (
            f"postgresql+asyncpg://{user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def safe_dump(self) -> dict[str, Any]:
        """Configuration snapshot for logs — secrets are masked."""
        data = self.model_dump()
        for key in ("api_key", "postgres_password", "openai_api_key", "telegram_bot_token"):
            if data.get(key) is not None:
                data[key] = "***"
        return data


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide settings singleton (overridable in tests via cache_clear)."""
    return Settings()
