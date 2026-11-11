"""API v1 router.

Stage 1 exposes metadata only; jobs, companies, technologies, stats and profile
endpoints are mounted here in Stage 3 without touching `app.main`.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

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
