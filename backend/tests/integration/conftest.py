"""Shared helpers and fixtures for integration tests."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.config import Settings
from app.main import create_app
from app.models import Technology
from app.normalization.taxonomy import load_taxonomy


async def insert_taxonomy(session: AsyncSession) -> None:
    taxonomy = load_taxonomy()
    session.add_all(
        Technology(
            slug=spec.slug,
            name=spec.name,
            category=spec.category,
            aliases=list(spec.aliases),
        )
        for spec in taxonomy.technologies
    )
    await session.flush()


@pytest.fixture()
async def taxonomy_rows(db_session: AsyncSession) -> None:
    """Seed the technology table inside the test transaction (opt-in)."""
    await insert_taxonomy(db_session)


@pytest.fixture()
def api_settings(settings: Settings) -> Settings:
    return settings.model_copy(update={"stats_cache_enabled": False})


@pytest_asyncio.fixture()
async def api_client(
    api_settings: Settings, db_session: AsyncSession
) -> AsyncIterator[httpx.AsyncClient]:
    """HTTP client that shares the test session and event loop with the test.

    `TestClient` runs requests in a separate thread/loop, which breaks asyncpg
    connections created by the test; ASGITransport keeps everything on one loop.
    """
    app = create_app(api_settings)

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = override_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()
