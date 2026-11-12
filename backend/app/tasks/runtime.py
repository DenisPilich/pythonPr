"""Process-local runtime for Celery tasks.

Celery's execution model is synchronous while the application is async. Each
worker process gets **one** event loop and **one** async engine, both created
lazily after the fork: an asyncpg connection is bound to the loop that created it,
so creating a new loop per task (the naive `asyncio.run()` approach) would break
connection reuse. `worker_process_init` resets the runtime in every child.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Coroutine
from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis

from app.ai.factory import build_ai_provider, build_fallback_provider
from app.core.config import Settings, get_settings
from app.core.redis import create_redis
from app.db.session import Database
from app.ports.ai_provider import AIProvider
from app.ports.vacancy_source import Notifier
from app.services.notification import LoggingNotifier


@dataclass
class TaskRuntime:
    settings: Settings
    database: Database
    redis: Redis
    provider: AIProvider
    fallback: AIProvider | None
    notifier: Notifier
    loop: asyncio.AbstractEventLoop


_runtime: TaskRuntime | None = None
_lock = threading.Lock()


def _build(settings: Settings | None = None) -> TaskRuntime:
    settings = settings or get_settings()
    provider = build_ai_provider(settings)
    return TaskRuntime(
        settings=settings,
        database=Database(settings),
        redis=create_redis(settings),
        provider=provider,
        fallback=build_fallback_provider(settings),
        notifier=LoggingNotifier(),
        loop=asyncio.new_event_loop(),
    )


def get_runtime() -> TaskRuntime:
    global _runtime
    with _lock:
        if _runtime is None:
            _runtime = _build()
        return _runtime


def configure_runtime(
    *,
    settings: Settings | None = None,
    database: Any = None,
    redis: Any = None,
    provider: AIProvider | None = None,
    fallback: AIProvider | None = None,
    notifier: Notifier | None = None,
) -> TaskRuntime:
    """Override dependencies in tests (or in a custom entrypoint)."""
    global _runtime
    base = _build(settings)
    runtime = TaskRuntime(
        settings=base.settings,
        database=database if database is not None else base.database,
        redis=redis if redis is not None else base.redis,
        provider=provider if provider is not None else base.provider,
        fallback=fallback if fallback is not None else base.fallback,
        notifier=notifier if notifier is not None else base.notifier,
        loop=base.loop,
    )
    with _lock:
        _runtime = runtime
    return runtime


def reset_runtime() -> None:
    global _runtime
    with _lock:
        runtime = _runtime
        _runtime = None
    if runtime is not None:
        runtime.loop.close()


def run_async[T](coro: Coroutine[Any, Any, T]) -> T:
    return get_runtime().loop.run_until_complete(coro)
