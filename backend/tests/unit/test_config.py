from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def build_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "_env_file": None,
        "environment": "test",
        "database_url": None,
        "postgres_password": "radar",
    }
    values.update(overrides)
    return Settings(**values)


def test_dsn_is_built_from_parts() -> None:
    settings = build_settings(
        postgres_host="db.internal",
        postgres_port=5433,
        postgres_user="radar",
        postgres_password="secret",
        postgres_db="jobs",
    )
    assert settings.sqlalchemy_dsn == "postgresql+asyncpg://radar:secret@db.internal:5433/jobs"


def test_password_is_url_encoded() -> None:
    settings = build_settings(postgres_password="p@ss:w/rd")
    assert "p%40ss%3Aw%2Frd" in settings.sqlalchemy_dsn


def test_explicit_database_url_wins() -> None:
    settings = build_settings(database_url="postgresql://u:p@h:5432/db")
    assert settings.sqlalchemy_dsn == "postgresql+asyncpg://u:p@h:5432/db"


def test_plain_postgres_scheme_is_normalized() -> None:
    settings = build_settings(database_url="postgres://u:p@h:5432/db")
    assert settings.sqlalchemy_dsn == "postgresql+asyncpg://u:p@h:5432/db"


def test_asyncpg_url_is_left_untouched() -> None:
    dsn = "postgresql+asyncpg://u:p@h:5432/db"
    assert build_settings(database_url=dsn).sqlalchemy_dsn == dsn


def test_empty_secret_strings_become_none() -> None:
    settings = build_settings(openai_api_key="", telegram_bot_token="   ")
    assert settings.openai_api_key is None
    assert settings.telegram_bot_token is None


@pytest.mark.parametrize("prefix", ["api/v1", "/api/v1/"])
def test_invalid_api_prefix_is_rejected(prefix: str) -> None:
    with pytest.raises(ValidationError):
        build_settings(api_v1_prefix=prefix)


def test_unknown_ai_provider_is_rejected() -> None:
    with pytest.raises(ValidationError):
        build_settings(ai_provider="magic")


def test_safe_dump_masks_secrets() -> None:
    settings = build_settings(api_key="super-secret", openai_api_key="sk-test")
    snapshot = settings.safe_dump()
    assert snapshot["api_key"] == "***"
    assert snapshot["openai_api_key"] == "***"
    assert snapshot["postgres_password"] == "***"
    assert settings.api_key.get_secret_value() == "super-secret"


def test_production_flag() -> None:
    assert build_settings(environment="production").is_production is True
    assert build_settings(environment="local").is_production is False
