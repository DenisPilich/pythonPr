"""Source lookups and health bookkeeping."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Source
from app.ports.vacancy_source import SourceConfig


class SourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_code(self, code: str) -> Source | None:
        return await self._session.scalar(select(Source).where(Source.code == code))

    async def list_enabled(self) -> list[Source]:
        result = await self._session.scalars(
            select(Source).where(Source.is_enabled.is_(True)).order_by(Source.code)
        )
        return list(result.all())

    async def get_config(self, code: str) -> SourceConfig | None:
        source = await self.get_by_code(code)
        if source is None:
            return None
        return SourceConfig(
            code=source.code,
            base_url=source.base_url,
            rate_limit_per_min=source.rate_limit_per_min,
            config=source.config,
        )

    async def mark_success(self, source_id: uuid.UUID) -> None:
        await self._session.execute(
            update(Source).where(Source.id == source_id).values(last_success_at=func.now())
        )
