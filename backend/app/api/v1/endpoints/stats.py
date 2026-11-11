"""`/stats` — dashboard aggregates, cached for 60 seconds in Redis."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.deps import SessionDep
from app.core.config import Settings
from app.schemas.stats import StatsResponse
from app.services.stats import StatsService


router = APIRouter(prefix="/stats", tags=["stats"])


@router.get(
    "",
    response_model=StatsResponse,
    summary="Dashboard statistics",
    description=(
        "Totals, source health, top technologies and companies, and distributions. "
        "Cached in Redis for 60 seconds; degrades to a direct query when Redis is down."
    ),
)
async def get_stats(request: Request, session: SessionDep) -> StatsResponse:
    settings: Settings = request.app.state.settings
    redis = getattr(request.app.state, "redis", None)
    service = StatsService(
        session,
        redis=redis,
        cache_enabled=settings.stats_cache_enabled,
    )
    return await service.overview()
