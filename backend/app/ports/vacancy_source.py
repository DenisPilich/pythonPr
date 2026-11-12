"""Ports: the contracts adapters implement and services depend on.

Services must not import `httpx`, `aiogram` or `openai`. These protocols are the
only reason those libraries are replaceable and testable with fakes.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from app.domain.dto import CollectedVacancy


@dataclass(frozen=True, slots=True)
class SourceConfig:
    """A `sources` row, detached from the ORM."""

    code: str
    base_url: str | None
    rate_limit_per_min: int
    config: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class CollectorContext:
    """Run-scoped parameters; per-source tuning lives in `SourceConfig.config`."""

    max_pages: int = 5


@dataclass(frozen=True, slots=True)
class CollectorPage:
    items: Sequence[Mapping[str, Any]]
    has_next: bool


@dataclass(slots=True)
class CollectorStats:
    fetched: int = 0
    mapped: int = 0
    skipped: int = 0


class VacancySource(Protocol):
    """A job board adapter."""

    code: str

    def collect(self, ctx: CollectorContext) -> AsyncIterator[CollectedVacancy]: ...


@dataclass(frozen=True, slots=True)
class NotificationMessage:
    chat_id: int
    text: str
    vacancy_id: uuid.UUID
    url: str


class Notifier(Protocol):
    """Delivery channel for a matched vacancy (implemented by the bot package)."""

    async def send_vacancy(self, message: NotificationMessage) -> int: ...
