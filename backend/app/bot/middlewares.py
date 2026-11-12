"""Bot middlewares: one session per update, user resolution, anti-flood.

A Telegram update gets exactly one database transaction: the session context
commits when the handler returns and rolls back on an exception. The user row is
created on first contact so every handler can rely on `db_user`.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy import select

from app.db.session import Database
from app.models import User


Handler = Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]]


class DbSessionMiddleware(BaseMiddleware):
    def __init__(self, database: Database) -> None:
        self._database = database

    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        async with self._database.session() as session:
            data["session"] = session
            return await handler(event, data)


class UserMiddleware(BaseMiddleware):
    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        session = data.get("session")
        from_user = getattr(event, "from_user", None)
        if session is None or from_user is None:
            return await handler(event, data)

        user = await session.scalar(select(User).where(User.telegram_id == from_user.id))
        if user is None:
            user = User(
                telegram_id=from_user.id,
                username=from_user.username,
                first_name=from_user.first_name,
            )
            session.add(user)
            await session.flush()
        else:
            user.username = from_user.username
            user.first_name = from_user.first_name
        user.last_seen_at = datetime.now(UTC)
        data["db_user"] = user
        return await handler(event, data)


class ThrottlingMiddleware(BaseMiddleware):
    """Very small in-process anti-flood; Redis-based limits belong to stage 8."""

    def __init__(self, min_interval_seconds: float = 0.4) -> None:
        self._interval = min_interval_seconds
        self._last_seen: dict[int, float] = {}

    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        from_user = getattr(event, "from_user", None)
        if from_user is None:
            return await handler(event, data)

        now = time.monotonic()
        previous = self._last_seen.get(from_user.id, 0.0)
        if now - previous < self._interval:
            if isinstance(event, CallbackQuery):
                await event.answer("Не так быстро 🙂", show_alert=False)
            elif isinstance(event, Message):
                await event.answer("Не так быстро 🙂")
            return None
        self._last_seen[from_user.id] = now
        return await handler(event, data)
