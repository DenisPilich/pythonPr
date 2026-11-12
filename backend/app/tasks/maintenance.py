"""Maintenance tasks: staleness sweep and statistics cache warming."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import update

from app.db.session import Database
from app.models import Vacancy
from app.services.stats import StatsService
from app.tasks.celery_app import celery_app
from app.tasks.runtime import get_runtime, run_async


async def deactivate_stale_async(database: Database, *, days: int) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    async with database.session() as session:
        result = await session.execute(
            update(Vacancy)
            .where(Vacancy.is_active.is_(True), Vacancy.last_seen_at < cutoff)
            .values(is_active=False)
        )
    return int(cast(Any, result).rowcount or 0)


async def refresh_stats_async(database: Database, redis: Any) -> dict[str, int]:
    async with database.session() as session:
        stats = await StatsService(session, redis=redis).overview()
    return {
        "vacancies": stats.vacancies.total,
        "technologies": len(stats.top_technologies),
    }


@celery_app.task(name="app.tasks.maintenance.deactivate_stale_vacancies")
def deactivate_stale_vacancies() -> int:
    runtime = get_runtime()
    return run_async(
        deactivate_stale_async(runtime.database, days=runtime.settings.stale_vacancy_days)
    )


@celery_app.task(name="app.tasks.maintenance.refresh_stats_cache")
def refresh_stats_cache() -> dict[str, int]:
    runtime = get_runtime()
    return run_async(refresh_stats_async(runtime.database, runtime.redis))
