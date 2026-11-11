"""In-process rate limiting.

Collection for one source is serialized by a distributed lock at the Celery layer
(stage 5), so a per-process limiter is sufficient: at most one collector instance
talks to a source at a time. The limiter reserves a slot under the lock and sleeps
outside it, which keeps concurrent callers correct without holding the lock during
I/O.
"""

from __future__ import annotations

import asyncio
import time


class AsyncRateLimiter:
    def __init__(self, per_minute: int) -> None:
        self._interval = 60.0 / per_minute if per_minute > 0 else 0.0
        self._lock = asyncio.Lock()
        self._next_at = 0.0

    async def wait(self) -> None:
        if self._interval <= 0:
            return
        async with self._lock:
            now = time.monotonic()
            delay = max(0.0, self._next_at - now)
            self._next_at = max(now, self._next_at) + self._interval
        if delay > 0:
            await asyncio.sleep(delay)
