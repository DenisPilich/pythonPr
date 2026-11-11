"""Shared HTTP client with retries, timeouts and structured logging.

The retry policy is deliberately simple and observable:
* transport/timeout errors and 5xx are retried with full-jitter exponential backoff;
* 429 honours `Retry-After` (seconds) and is retried the same way;
* other 4xx fail fast — retrying a 404 only wastes the source's quota;
* `max_retries` attempts *after* the first one, then `SourceUnavailableError`.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any

import httpx
import structlog

from app.collectors.errors import SourceResponseError, SourceUnavailableError
from app.core.config import Settings


logger = structlog.get_logger(__name__)

_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


def _retry_after_seconds(response: httpx.Response) -> float | None:
    raw = response.headers.get("retry-after")
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        return None


class HttpClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(settings.http_timeout_seconds),
            limits=httpx.Limits(max_connections=settings.http_max_connections),
            headers={
                "User-Agent": settings.http_user_agent,
                "Accept": "application/json, application/rss+xml, text/xml, */*",
            },
            follow_redirects=True,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    def _backoff(self, attempt: int) -> float:
        ceiling = min(
            self._settings.http_retry_max_seconds,
            self._settings.http_retry_base_seconds * (2**attempt),
        )
        return random.uniform(0.0, ceiling)

    async def get(self, url: str, *, params: dict[str, Any] | None = None) -> httpx.Response:
        last_error: Exception | None = None
        retry_after: float | None = None

        for attempt in range(self._settings.http_max_retries + 1):
            retry_after = None
            try:
                response = await self._client.get(url, params=params)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
            else:
                if response.status_code < 400:
                    return response
                if response.status_code in _RETRYABLE_STATUS:
                    last_error = SourceUnavailableError(f"{url} returned {response.status_code}")
                    retry_after = _retry_after_seconds(response)
                else:
                    raise SourceResponseError(
                        f"{url} returned {response.status_code}: {response.text[:200]}"
                    )

            if attempt >= self._settings.http_max_retries:
                break
            delay = retry_after if retry_after is not None else self._backoff(attempt)
            logger.warning(
                "http_retry",
                url=url,
                attempt=attempt + 1,
                delay_seconds=round(delay, 3),
                error=type(last_error).__name__ if last_error else None,
                status=retry_after,
            )
            await asyncio.sleep(delay)

        raise SourceUnavailableError(f"{url} failed after retries: {last_error}") from last_error

    async def get_json(self, url: str, *, params: dict[str, Any] | None = None) -> Any:
        response = await self.get(url, params=params)
        try:
            return response.json()
        except ValueError as exc:
            raise SourceResponseError(f"{url} returned invalid JSON") from exc

    async def get_bytes(self, url: str) -> bytes:
        response = await self.get(url)
        return response.content
