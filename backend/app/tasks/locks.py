"""Distributed lock on Redis.

`SET NX PX` makes collection runs mutually exclusive across workers; the release
is a compare-and-delete so a task that overran its TTL cannot delete a lock that
another worker has already acquired.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from redis.asyncio import Redis


class LockNotAcquiredError(RuntimeError):
    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"lock {key!r} is held by another worker")


@asynccontextmanager
async def redis_lock(redis: Redis, key: str, *, ttl_seconds: int = 600) -> AsyncIterator[None]:
    token = uuid.uuid4().hex
    acquired = await redis.set(key, token, nx=True, px=ttl_seconds * 1000)
    if not acquired:
        raise LockNotAcquiredError(key)
    try:
        yield
    finally:
        current = await redis.get(key)
        if current == token:
            await redis.delete(key)
