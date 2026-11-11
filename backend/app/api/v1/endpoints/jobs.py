"""`/jobs` — filtered, sorted, paginated vacancy search."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from app.api.deps import PaginationDep, SessionDep, TelegramIdDep, require_api_key
from app.api.v1.mappers import analysis_to_read, job_to_detail, job_to_list_item
from app.core.exceptions import NotFoundError
from app.domain.enums import SeniorityLevel, VacancyLanguage, WorkFormat
from app.repositories.analyses import AnalysisRepository
from app.repositories.jobs import JobFilters, JobRepository
from app.schemas.analysis import AnalysisRead
from app.schemas.common import JobSortField, Page, SortOrder
from app.schemas.jobs import JOB_LIST_EXAMPLE, JobDetail, JobListItem
from app.services.analysis import AnalysisService
from app.services.profile import ProfileService


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


@router.post(
    "/{job_id}/analyze",
    response_model=AnalysisRead,
    summary="Analyse a vacancy for the current profile",
    description=(
        "Requires `X-API-Key`. Runs the hard prefilters, then the configured AI provider; "
        "cached results are returned with `X-Analysis-Cached: true`. "
        "Filtered vacancies are stored with provider `prefilter` and score 0."
    ),
    dependencies=[Depends(require_api_key)],
    responses={
        401: {"description": "Missing or invalid API key"},
        404: {"description": "Vacancy or profile not found"},
        429: {"description": "Daily AI budget exhausted"},
    },
)
async def analyze_job(
    job_id: uuid.UUID,
    request: Request,
    response: Response,
    session: SessionDep,
    telegram_id: TelegramIdDep,
) -> AnalysisRead:
    profile = await ProfileService(session).get(telegram_id)
    settings = request.app.state.settings
    service = AnalysisService(
        session,
        provider=request.app.state.ai_provider,
        settings=settings,
        fallback=getattr(request.app.state, "ai_fallback", None),
    )
    outcome = await service.analyze(vacancy_id=job_id, user_id=profile.user_id)
    response.headers["X-Analysis-Cached"] = "true" if outcome.cached else "false"
    response.headers["X-Analysis-Skipped"] = "true" if outcome.skipped else "false"
    return analysis_to_read(outcome.analysis)


@router.get(
    "/{job_id}/analysis",
    response_model=AnalysisRead,
    summary="Latest analysis for a vacancy",
    description="Returns the most recent analysis for the current profile, if any.",
    responses={404: {"description": "No analysis for this vacancy and profile"}},
)
async def get_job_analysis(
    job_id: uuid.UUID, session: SessionDep, telegram_id: TelegramIdDep
) -> AnalysisRead:
    profile = await ProfileService(session).get(telegram_id)
    analysis = await AnalysisRepository(session).latest(job_id, profile.user_id)
    if analysis is None:
        raise NotFoundError(f"No analysis for vacancy {job_id} yet")
    return analysis_to_read(analysis)
