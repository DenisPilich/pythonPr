"""Reference data seeding: sources and the technology taxonomy.

Idempotent by design (`INSERT ... ON CONFLICT DO UPDATE`), so it is safe to run on
every container start and from tests. Operator-controlled flags (`is_enabled`) are
deliberately not overwritten.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import SourceKind
from app.models import Source, Technology
from app.normalization.taxonomy import Taxonomy, load_taxonomy


@dataclass(frozen=True, slots=True)
class SourceSeed:
    code: str
    name: str
    kind: SourceKind
    base_url: str
    rate_limit_per_min: int
    config: dict[str, Any]


SOURCES: tuple[SourceSeed, ...] = (
    SourceSeed(
        code="hh",
        name="hh.ru",
        kind=SourceKind.JSON_API,
        base_url="https://api.hh.ru",
        rate_limit_per_min=10,
        config={
            "text": ["python", "fastapi", "django"],
            "per_page": 20,
            "max_pages": 5,
            "area": 113,
        },
    ),
    SourceSeed(
        code="remoteok",
        name="RemoteOK",
        kind=SourceKind.JSON_API,
        base_url="https://remoteok.com/api",
        rate_limit_per_min=10,
        config={"max_items": 200},
    ),
    SourceSeed(
        code="remotive",
        name="Remotive",
        kind=SourceKind.JSON_API,
        base_url="https://remotive.com/api/remote-jobs",
        rate_limit_per_min=10,
        config={"limit": 100},
    ),
    SourceSeed(
        code="arbeitnow",
        name="Arbeitnow",
        kind=SourceKind.JSON_API,
        base_url="https://www.arbeitnow.com/api/job-board-api",
        rate_limit_per_min=20,
        config={"max_pages": 3},
    ),
    SourceSeed(
        code="weworkremotely",
        name="We Work Remotely (RSS)",
        kind=SourceKind.RSS,
        base_url="https://weworkremotely.com/categories/remote-programming-jobs.rss",
        rate_limit_per_min=5,
        config={"max_items": 100},
    ),
)


@dataclass(frozen=True, slots=True)
class SeedReport:
    sources: int
    technologies: int


async def seed_reference_data(
    session: AsyncSession, *, taxonomy: Taxonomy | None = None
) -> SeedReport:
    taxonomy = taxonomy or load_taxonomy()

    source_rows: list[dict[str, Any]] = [
        {
            "code": source.code,
            "name": source.name,
            "kind": source.kind,
            "base_url": source.base_url,
            "rate_limit_per_min": source.rate_limit_per_min,
            "config": source.config,
        }
        for source in SOURCES
    ]
    source_stmt = pg_insert(Source).values(source_rows)
    source_stmt = source_stmt.on_conflict_do_update(
        index_elements=[Source.code],
        set_={
            "name": source_stmt.excluded.name,
            "kind": source_stmt.excluded.kind,
            "base_url": source_stmt.excluded.base_url,
            "rate_limit_per_min": source_stmt.excluded.rate_limit_per_min,
            "config": source_stmt.excluded.config,
        },
    )
    await session.execute(source_stmt)

    technology_rows: list[dict[str, Any]] = [
        {
            "slug": spec.slug,
            "name": spec.name,
            "category": spec.category,
            "aliases": list(spec.aliases),
        }
        for spec in taxonomy.technologies
    ]
    technology_stmt = pg_insert(Technology).values(technology_rows)
    technology_stmt = technology_stmt.on_conflict_do_update(
        index_elements=[Technology.slug],
        set_={
            "name": technology_stmt.excluded.name,
            "category": technology_stmt.excluded.category,
            "aliases": technology_stmt.excluded.aliases,
        },
    )
    await session.execute(technology_stmt)

    return SeedReport(sources=len(source_rows), technologies=len(technology_rows))
