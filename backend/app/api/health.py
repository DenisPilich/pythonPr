"""Liveness and readiness probes.

`/health/live` answers "is the process up?" and must never touch dependencies.
`/health/ready` answers "can this instance serve traffic?" and reports each
dependency separately so a failing Redis is distinguishable from a failing DB.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Request, Response
from redis.asyncio import Redis

from app.core.config import Settings
from app.db.session import Database
from app.schemas.health import HealthResponse


router = APIRouter(tags=["health"])
logger = structlog.get_logger(__name__)


@router.get(
    "/health/live",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Returns 200 as long as the process is running. Used by orchestration.",
)
async def liveness(request: Request) -> HealthResponse:
    settings: Settings = request.app.state.settings
    return HealthResponse(status="ok", version=settings.version)


@router.get(
    "/health/ready",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse, "description": "One or more dependencies are down"}},
    summary="Readiness probe",
    description="Checks PostgreSQL and Redis connectivity; 503 when either is unavailable.",
)
async def readiness(request: Request, response: Response) -> HealthResponse:
    settings: Settings = request.app.state.settings
    database: Database = request.app.state.db
    redis: Redis = request.app.state.redis

    checks: dict[str, str] = {}
    healthy = True

    try:
        await database.ping()
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {type(exc).__name__}"
        healthy = False

    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {type(exc).__name__}"
        healthy = False

    if not healthy:
        response.status_code = 503
        logger.warning("readiness_failed", checks=checks)

    return HealthResponse(
        status="ok" if healthy else "degraded",
        version=settings.version,
        checks=checks,
    )
