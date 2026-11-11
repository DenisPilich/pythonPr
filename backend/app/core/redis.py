"""Redis connection helpers (cache, locks and Celery broker share one instance)."""

from __future__ import annotations

from redis.asyncio import Redis

from app.core.config import Settings


def create_redis(settings: Settings) -> Redis:
    """Create a lazily connected client; `ping()` or first command opens the socket."""
    return Redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        health_check_interval=30,
        socket_connect_timeout=5,
        socket_timeout=5,
    )
