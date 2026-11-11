"""Collection use case: source → collector → normalizer → database.

Transaction boundaries are chosen for the job: the collector fetches everything
first (network, no transaction held), then one transaction ingests the batch, and
the `collector_runs` row is written in its own short transaction so a failed run is
still visible. Batch-per-vacancy commits would be preferable for very large
sources; that is a documented scaling step, not a stage-2 requirement.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

import structlog

from app.collectors.base import BaseCollector
from app.db.session import Database
from app.domain.enums import CollectorRunStatus
from app.normalization.pipeline import NormalizationPipeline
from app.ports.vacancy_source import CollectorContext, SourceConfig
from app.repositories.runs import CollectorRunRepository
from app.repositories.sources import SourceRepository
from app.services.ingest import IngestService


logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class CollectionReport:
    source_code: str
    status: CollectorRunStatus
    fetched: int
    created: int
    updated: int
    duplicates: int
    skipped: int
    duration_ms: int
    error: str | None = None


class CollectionService:
    def __init__(self, database: Database, pipeline: NormalizationPipeline) -> None:
        self._database = database
        self._pipeline = pipeline

    async def run(
        self,
        source: SourceConfig,
        source_id: uuid.UUID,
        collector: BaseCollector,
        *,
        max_pages: int = 5,
        task_id: str | None = None,
    ) -> CollectionReport:
        started = time.monotonic()
        run_id = await self._start_run(source_id, task_id)

        created = updated = duplicates = 0
        try:
            collected = [
                item async for item in collector.collect(CollectorContext(max_pages=max_pages))
            ]
        except Exception as exc:
            await self._finish(
                run_id,
                status=CollectorRunStatus.FAILED,
                fetched=collector.stats.fetched,
                created=0,
                updated=0,
                skipped=collector.stats.skipped,
                duration_ms=self._elapsed_ms(started),
                error=f"{type(exc).__name__}: {exc}"[:2000],
            )
            raise

        try:
            async with self._database.session() as session:
                ingest = IngestService(session)
                for item in collected:
                    outcome = await ingest.ingest(self._pipeline.normalize(item), source_id)
                    if outcome.status == "created":
                        created += 1
                    elif outcome.status == "updated":
                        updated += 1
                    else:
                        duplicates += 1
                await SourceRepository(session).mark_success(source_id)
        except Exception as exc:
            await self._finish(
                run_id,
                status=CollectorRunStatus.FAILED,
                fetched=collector.stats.fetched,
                created=created,
                updated=updated,
                skipped=collector.stats.skipped,
                duration_ms=self._elapsed_ms(started),
                error=f"{type(exc).__name__}: {exc}"[:2000],
            )
            raise

        status = (
            CollectorRunStatus.PARTIAL if collector.stats.skipped else CollectorRunStatus.SUCCESS
        )
        duration_ms = self._elapsed_ms(started)
        await self._finish(
            run_id,
            status=status,
            fetched=collector.stats.fetched,
            created=created,
            updated=updated,
            skipped=collector.stats.skipped,
            duration_ms=duration_ms,
            error=None,
        )
        logger.info(
            "source_collected",
            source=source.code,
            status=status.value,
            fetched=collector.stats.fetched,
            created=created,
            updated=updated,
            duplicates=duplicates,
            skipped=collector.stats.skipped,
            duration_ms=duration_ms,
        )
        return CollectionReport(
            source_code=source.code,
            status=status,
            fetched=collector.stats.fetched,
            created=created,
            updated=updated,
            duplicates=duplicates,
            skipped=collector.stats.skipped,
            duration_ms=duration_ms,
        )

    async def _start_run(self, source_id: uuid.UUID, task_id: str | None) -> uuid.UUID:
        async with self._database.session() as session:
            return await CollectorRunRepository(session).start(source_id, task_id)

    async def _finish(
        self,
        run_id: uuid.UUID,
        *,
        status: CollectorRunStatus,
        fetched: int,
        created: int,
        updated: int,
        skipped: int,
        duration_ms: int,
        error: str | None,
    ) -> None:
        async with self._database.session() as session:
            await CollectorRunRepository(session).finish(
                run_id,
                status=status,
                items_fetched=fetched,
                items_created=created,
                items_updated=updated,
                items_skipped=skipped,
                duration_ms=duration_ms,
                error=error,
            )

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return max(0, int((time.monotonic() - started) * 1000))
