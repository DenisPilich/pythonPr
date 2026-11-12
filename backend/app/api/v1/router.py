"""API v1 router.

Endpoint modules are mounted here; `app.main` only knows the prefix and this
router, so adding a resource never touches application wiring.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.v1.endpoints import companies, history, jobs, profile, stats, technologies
from app.core.config import Settings
from app.schemas.meta import MetaResponse


router = APIRouter()


@router.get(
    "/meta",
    response_model=MetaResponse,
    tags=["meta"],
    summary="Service metadata",
    description="Name, version and environment of the running API instance.",
)
async def get_meta(request: Request) -> MetaResponse:
    settings: Settings = request.app.state.settings
    return MetaResponse(
        name=settings.app_name,
        version=settings.version,
        environment=settings.environment,
        api_prefix=settings.api_v1_prefix,
        docs_url="/docs",
    )


router.include_router(jobs.router)
router.include_router(companies.router)
router.include_router(technologies.router)
router.include_router(stats.router)
router.include_router(profile.router)
router.include_router(history.router)
