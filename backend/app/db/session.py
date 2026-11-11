"""Async engine and unit-of-work helpers.

Transaction policy: one transaction per request/task. Callers `flush()`; the
context manager commits on a clean exit and rolls back on an exception. This
keeps commit points in exactly one place and makes multi-step ingestion atomic.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings


class Database:
    """Owns the engine and session factory for one process."""

    def __init__(self, settings: Settings) -> None:
        self._engine: AsyncEngine = create_async_engine(
            settings.sqlalchemy_dsn,
            echo=settings.db_echo,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_pre_ping=True,
        )
        self._session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
            autoflush=False,
        )

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Unit of work: commit on success, rollback on any exception."""
        async with self._session_factory() as session, session.begin():
            yield session

    async def ping(self) -> None:
        async with self._engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def dispose(self) -> None:
        await self._engine.dispose()
