from __future__ import annotations

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seed import SOURCES, seed_reference_data
from app.models import Source, Technology


pytestmark = pytest.mark.integration


async def test_seed_is_idempotent(db_session: AsyncSession) -> None:
    first = await seed_reference_data(db_session)
    second = await seed_reference_data(db_session)

    assert first.sources == second.sources == len(SOURCES)
    assert first.technologies == second.technologies
    assert first.technologies >= 70

    source_count = await db_session.scalar(select(func.count()).select_from(Source))
    technology_count = await db_session.scalar(select(func.count()).select_from(Technology))
    assert source_count == len(SOURCES)
    assert technology_count == second.technologies


async def test_seed_creates_expected_sources(db_session: AsyncSession) -> None:
    await seed_reference_data(db_session)
    codes = set((await db_session.scalars(select(Source.code))).all())
    assert codes == {"hh", "remoteok", "remotive", "arbeitnow", "weworkremotely"}


async def test_seed_preserves_operator_flags(db_session: AsyncSession) -> None:
    await seed_reference_data(db_session)
    await db_session.execute(update(Source).where(Source.code == "hh").values(is_enabled=False))

    await seed_reference_data(db_session)

    enabled = await db_session.scalar(select(Source.is_enabled).where(Source.code == "hh"))
    assert enabled is False


async def test_seed_upserts_aliases(db_session: AsyncSession) -> None:
    await seed_reference_data(db_session)
    postgres = await db_session.scalar(select(Technology).where(Technology.slug == "postgresql"))
    assert postgres is not None
    assert "postgres" in postgres.aliases
