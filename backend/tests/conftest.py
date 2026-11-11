"""Shared pytest fixtures.

Unit tests need nothing external. Integration tests require `TEST_DATABASE_URL`
(and, for readiness, `TEST_REDIS_URL`) and are skipped otherwise, so a fresh
clone can run `pytest` before Docker is up.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from urllib.parse import urlparse

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401  # populate Base.metadata
from app.core.config import Settings
from app.db.base import Base
from app.main import create_app


BACKEND_DIR = Path(__file__).resolve().parents[1]
TRUNCATE_TABLES = ", ".join(table.name for table in reversed(Base.metadata.sorted_tables))


async def _truncate_all(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(f"TRUNCATE TABLE {TRUNCATE_TABLES} RESTART IDENTITY CASCADE")
            )
    finally:
        await engine.dispose()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.getenv("TEST_DATABASE_URL"):
        return
    skip = pytest.mark.skip(reason="TEST_DATABASE_URL is not set; integration tests skipped")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)


@pytest.fixture()
def settings() -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        environment="test",
        api_key="test-key",
        database_url="postgresql+asyncpg://radar:radar@localhost:5432/radar_test",
        redis_url=os.getenv("TEST_REDIS_URL", "redis://localhost:6379/15"),
        log_json=False,
    )


@pytest.fixture()
def client(settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


# --- integration -----------------------------------------------------------


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set")
    database_name = urlparse(url).path.lstrip("/")
    if not database_name.endswith("_test"):
        pytest.fail(
            "TEST_DATABASE_URL must point to a database whose name ends with '_test' "
            f"(got {database_name!r}); the suite truncates all tables"
        )
    return url


@pytest.fixture(scope="session")
def migrated_database(database_url: str) -> str:
    """Apply migrations once per session, then start from a clean schema."""
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env={**os.environ, "DATABASE_URL": database_url},
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(f"alembic upgrade failed:\n{result.stdout}\n{result.stderr}")
    asyncio.run(_truncate_all(database_url))
    return database_url


@pytest_asyncio.fixture()
async def engine(migrated_database: str) -> AsyncIterator[AsyncEngine]:
    test_engine = create_async_engine(migrated_database, poolclass=NullPool)
    try:
        yield test_engine
    finally:
        await test_engine.dispose()


@pytest_asyncio.fixture()
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Session bound to an outer transaction that is always rolled back."""
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()


@pytest.fixture()
def integration_client(settings: Settings, migrated_database: str) -> Iterator[TestClient]:
    integration_settings = settings.model_copy(
        update={
            "database_url": migrated_database,
            "redis_url": os.getenv("TEST_REDIS_URL", "redis://localhost:6379/15"),
        }
    )
    app = create_app(integration_settings)
    with TestClient(app) as test_client:
        yield test_client
