"""Collection tasks: one task per source, guarded by a distributed lock."""

from __future__ import annotations

from typing import Any

from app.collectors.errors import CollectorError
from app.collectors.http import HttpClient
from app.collectors.registry import build_collector
from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.db.session import Database
from app.normalization.pipeline import NormalizationPipeline
from app.ports.vacancy_source import SourceConfig
from app.repositories.sources import SourceRepository
from app.services.collection import CollectionService
from app.tasks.celery_app import celery_app
from app.tasks.locks import LockNotAcquiredError, redis_lock
from app.tasks.runtime import get_runtime, run_async


LOCK_TTL_SECONDS = 900


async def load_source_config(database: Database, code: str) -> tuple[Any, SourceConfig]:
    async with database.session() as session:
        source = await SourceRepository(session).get_by_code(code)
        if source is None:
            raise ConfigurationError(f"unknown source: {code!r}")
        return source.id, SourceConfig(
            code=source.code,
            base_url=source.base_url,
            rate_limit_per_min=source.rate_limit_per_min,
            config=source.config,
        )


async def collect_source_async(
    code: str,
    *,
    database: Database,
    redis: Any,
    settings: Settings,
    max_pages: int = 5,
    task_id: str | None = None,
) -> dict[str, Any]:
    source_id, config = await load_source_config(database, code)
    lock_key = f"lock:collect:{code}"

    try:
        async with redis_lock(redis, lock_key, ttl_seconds=LOCK_TTL_SECONDS):
            http = HttpClient(settings)
            try:
                collector = build_collector(config, http, settings)
                service = CollectionService(database, NormalizationPipeline())
                report = await service.run(
                    config,
                    source_id,
                    collector,
                    max_pages=max_pages,
                    task_id=task_id,
                )
            finally:
                await http.aclose()
    except LockNotAcquiredError:
        return {"source": code, "status": "locked"}

    return {
        "source": report.source_code,
        "status": report.status.value,
        "fetched": report.fetched,
        "created": report.created,
        "updated": report.updated,
        "duplicates": report.duplicates,
        "skipped": report.skipped,
        "duration_ms": report.duration_ms,
    }


async def enabled_source_codes(database: Database) -> list[str]:
    async with database.session() as session:
        sources = await SourceRepository(session).list_enabled()
        return [source.code for source in sources]


@celery_app.task(
    bind=True,
    name="app.tasks.collection.collect_source",
    autoretry_for=(CollectorError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
    soft_time_limit=600,
    time_limit=660,
)
def collect_source(self: Any, code: str, max_pages: int = 5) -> dict[str, Any]:
    runtime = get_runtime()
    return run_async(
        collect_source_async(
            code,
            database=runtime.database,
            redis=runtime.redis,
            settings=runtime.settings,
            max_pages=max_pages,
            task_id=self.request.id,
        )
    )


@celery_app.task(name="app.tasks.collection.collect_all_sources")
def collect_all_sources() -> list[str]:
    runtime = get_runtime()
    codes = run_async(enabled_source_codes(runtime.database))
    for code in codes:
        collect_source.delay(code)
    return codes
