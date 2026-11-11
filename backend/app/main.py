"""FastAPI application factory.

Run with `uvicorn app.main:create_app --factory` (Docker uses exactly this), or
import `create_app` in tests with overridden settings.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import (
    app_error_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.api.health import router as health_router
from app.api.middleware import RequestContextMiddleware
from app.api.v1.router import router as v1_router
from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.core.redis import create_redis
from app.db.session import Database


logger = structlog.get_logger(__name__)

DESCRIPTION = """
**AI Job Radar** collects developer vacancies from several public sources,
normalizes them into a single model, scores every vacancy against a user profile
with an LLM, and delivers the relevant ones to Telegram.

* `GET /health/live`, `GET /health/ready` — probes
* `GET /api/v1/jobs`, `/jobs/{id}` — search and detail
* `GET /api/v1/companies`, `/technologies`, `/stats` — catalogs and dashboard data
* `GET|POST|PUT /api/v1/profile` — matching profile (writes require `X-API-Key`)
"""

OPENAPI_TAGS: list[dict[str, Any]] = [
    {"name": "health", "description": "Liveness and readiness probes."},
    {"name": "meta", "description": "Service metadata and version."},
    {"name": "jobs", "description": "Vacancy search and detail."},
    {"name": "companies", "description": "Employers and their vacancy counts."},
    {"name": "technologies", "description": "Technology demand catalog."},
    {"name": "stats", "description": "Dashboard aggregates."},
    {"name": "profile", "description": "User matching profile."},
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    database = Database(settings)
    redis = create_redis(settings)
    app.state.db = database
    app.state.redis = redis

    logger.info(
        "application_starting",
        environment=settings.environment,
        version=settings.version,
    )
    try:
        yield
    finally:
        await redis.aclose()
        await database.dispose()
        logger.info("application_stopped")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description=DESCRIPTION,
        openapi_tags=OPENAPI_TAGS,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = settings

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.include_router(health_router)
    app.include_router(v1_router, prefix=settings.api_v1_prefix)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "version": settings.version,
            "docs": "/docs",
            "api": settings.api_v1_prefix,
        }

    return app
