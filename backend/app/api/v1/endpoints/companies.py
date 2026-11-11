"""`/companies` — employers ordered by vacancy count or name."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import PaginationDep, SessionDep
from app.repositories.catalog import CompanyRepository
from app.schemas.catalog import CompanyRead
from app.schemas.common import Page


router = APIRouter(prefix="/companies", tags=["companies"])


class CompanySort(StrEnum):
    VACANCIES = "vacancies"
    NAME = "name"


@router.get(
    "",
    response_model=Page[CompanyRead],
    summary="List companies",
    description="Companies with their vacancy counts, optionally filtered by name.",
)
async def list_companies(
    session: SessionDep,
    pagination: PaginationDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    sort: CompanySort = CompanySort.VACANCIES,
) -> Page[CompanyRead]:
    rows, total = await CompanyRepository(session).list_companies(
        q=q,
        sort_by_vacancies=sort is CompanySort.VACANCIES,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return Page[CompanyRead](
        items=[
            CompanyRead(
                id=row.company.id,
                name=row.company.name,
                normalized_name=row.company.normalized_name,
                website=row.company.website,
                logo_url=row.company.logo_url,
                vacancy_count=row.vacancy_count,
            )
            for row in rows
        ],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )
