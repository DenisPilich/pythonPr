"""Shared FastAPI dependencies."""

from __future__ import annotations

import secrets
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import UnauthorizedError
from app.db.session import Database


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    database: Database = request.app.state.db
    async with database.session() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def require_api_key(
    request: Request,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    """Guard write endpoints. The demo deployment has one shared key."""
    settings: Settings = request.app.state.settings
    expected = settings.api_key.get_secret_value()
    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise UnauthorizedError("Missing or invalid X-API-Key header")


ApiKeyDep = Annotated[None, Depends(require_api_key)]


async def get_telegram_id(
    request: Request,
    x_telegram_id: Annotated[int | None, Header(alias="X-Telegram-Id", ge=1)] = None,
) -> int:
    if x_telegram_id is not None:
        return x_telegram_id
    settings: Settings = request.app.state.settings
    return settings.demo_telegram_id


TelegramIdDep = Annotated[int, Depends(get_telegram_id)]


@dataclass(frozen=True, slots=True)
class Pagination:
    limit: int
    offset: int


def pagination_params(
    limit: Annotated[int, Query(ge=1, le=100, description="Page size")] = 20,
    offset: Annotated[int, Query(ge=0, description="Rows to skip")] = 0,
) -> Pagination:
    return Pagination(limit=limit, offset=offset)


PaginationDep = Annotated[Pagination, Depends(pagination_params)]
