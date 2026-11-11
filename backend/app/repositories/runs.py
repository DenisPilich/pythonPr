"""Collector run ledger: start, finish, counters, error text."""

from __future__ import annotations

import uuid

from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import CollectorRunStatus
from app.models import CollectorRun


class CollectorRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def start(self, source_id: uuid.UUID, celery_task_id: str | None) -> uuid.UUID:
        run = CollectorRun(source_id=source_id, celery_task_id=celery_task_id)
        self._session.add(run)
        await self._session.flush()
        return run.id

    async def finish(
        self,
        run_id: uuid.UUID,
        *,
        status: CollectorRunStatus,
        items_fetched: int,
        items_created: int,
        items_updated: int,
        items_skipped: int,
        duration_ms: int,
        error: str | None = None,
    ) -> None:
        await self._session.execute(
            update(CollectorRun)
            .where(CollectorRun.id == run_id)
            .values(
                status=status,
                finished_at=func.now(),
                items_fetched=items_fetched,
                items_created=items_created,
                items_updated=items_updated,
                items_skipped=items_skipped,
                duration_ms=duration_ms,
                error=error,
            )
        )
