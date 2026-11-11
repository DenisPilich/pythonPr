"""`/jobs` — filtered, sorted, paginated vacancy search."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import PaginationDep, SessionDep
from app.api.v1.mappers import job_to_detail, job_to_list_item
from app.core.exceptions import NotFoundError
from app.domain.enums import SeniorityLevel, VacancyLanguage, WorkFormat
from app.repositories.jobs import JobFilters, JobRepository
from app.schemas.common import JobSortField, Page, SortOrder
from app.schemas.jobs import JOB_LIST_EXAMPLE, JobDetail, JobListItem


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get(
    "",
    response_model=Page[JobListItem],
    summary="Search vacancies",
    description=(
        "Full-text search over title and description, plus filters for source, company, "
        "technology, seniority, work format, language, salary and publication date. "
        "Repeat a filter to OR its values: `?technology=python&technology=docker`."
    ),
    responses={200: {"content": {"application/json": {"example": JOB_LIST_EXAMPLE}}}},
)
async def list_jobs(
    session: SessionDep,
    pagination: PaginationDep,
    q: Annotated[str | None, Query(max_length=200, description="Full-text query")] = None,
    source: Annotated[str | None, Query(max_length=32, description="Source code")] = None,
    company: Annotated[
        str | None, Query(max_length=100, description="Company name substring")
    ] = None,
    technology: Annotated[list[str] | None, Query(description="Technology slugs")] = None,
    seniority: Annotated[list[SeniorityLevel] | None, Query()] = None,
    work_format: Annotated[list[WorkFormat] | None, Query()] = None,
    language: Annotated[list[VacancyLanguage] | None, Query()] = None,
    min_salary: Annotated[Decimal | None, Query(ge=0, description="Monthly EUR floor")] = None,
    max_salary: Annotated[Decimal | None, Query(ge=0, description="Monthly EUR ceiling")] = None,
    published_after: datetime | None = None,
    published_before: datetime | None = None,
    include_inactive: bool = False,
    sort: JobSortField = JobSortField.PUBLISHED_AT,
    order: SortOrder = SortOrder.DESC,
) -> Page[JobListItem]:
    filters = JobFilters(
        q=q,
        source=source,
        company=company,
        technologies=tuple(technology or ()),
        seniority=tuple(seniority or ()),
        work_formats=tuple(work_format or ()),
        languages=tuple(language or ()),
        min_salary_eur=min_salary,
        max_salary_eur=max_salary,
        published_after=published_after,
        published_before=published_before,
        include_inactive=include_inactive,
    )
    page = await JobRepository(session).list_jobs(
        filters,
        sort=sort,
        descending=order is SortOrder.DESC,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return Page[JobListItem](
        items=[job_to_list_item(vacancy) for vacancy in page.items],
        total=page.total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.get(
    "/{job_id}",
    response_model=JobDetail,
    summary="Vacancy detail",
    description="Full cleaned description plus provenance (every source that delivered it).",
    responses={404: {"description": "Vacancy not found"}},
)
async def get_job(job_id: uuid.UUID, session: SessionDep) -> JobDetail:
    vacancy = await JobRepository(session).get_job(job_id)
    if vacancy is None:
        raise NotFoundError(f"Vacancy {job_id} not found")
    return job_to_detail(vacancy)
