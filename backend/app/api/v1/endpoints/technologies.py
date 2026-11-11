"""`/technologies` — the catalog with demand counts."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import PaginationDep, SessionDep
from app.domain.enums import TechnologyCategory
from app.repositories.catalog import TechnologyRepository
from app.schemas.catalog import TechnologyRead
from app.schemas.common import Page


router = APIRouter(prefix="/technologies", tags=["technologies"])


@router.get(
    "",
    response_model=Page[TechnologyRead],
    summary="List technologies",
    description="Canonical technology catalog, ordered by how many vacancies mention it.",
)
async def list_technologies(
    session: SessionDep,
    pagination: PaginationDep,
    q: Annotated[str | None, Query(max_length=64)] = None,
    category: TechnologyCategory | None = None,
) -> Page[TechnologyRead]:
    rows, total = await TechnologyRepository(session).list_technologies(
        q=q,
        category=category,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return Page[TechnologyRead](
        items=[
            TechnologyRead(
                id=row.technology.id,
                slug=row.technology.slug,
                name=row.technology.name,
                category=row.technology.category,
                aliases=row.technology.aliases,
                vacancy_count=row.vacancy_count,
            )
            for row in rows
        ],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )
