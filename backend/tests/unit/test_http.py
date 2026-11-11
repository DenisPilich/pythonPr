from __future__ import annotations

import httpx
import pytest
import respx

from app.collectors.errors import SourceResponseError, SourceUnavailableError
from app.collectors.http import HttpClient
from app.core.config import Settings


@pytest.fixture()
def fast_retries(settings: Settings) -> Settings:
    return settings.model_copy(
        update={
            "http_max_retries": 2,
            "http_retry_base_seconds": 0.0,
            "http_retry_max_seconds": 0.0,
            "http_timeout_seconds": 1.0,
        }
    )


async def test_retries_on_server_error(fast_retries: Settings) -> None:
    client = HttpClient(fast_retries)
    try:
        with respx.mock:
            route = respx.get("https://example.com/jobs").mock(
                side_effect=[
                    httpx.Response(500),
                    httpx.Response(200, json={"ok": True}),
                ]
            )
            payload = await client.get_json("https://example.com/jobs")
    finally:
        await client.aclose()

    assert payload == {"ok": True}
    assert route.call_count == 2


async def test_honours_retry_after(fast_retries: Settings) -> None:
    client = HttpClient(fast_retries)
    try:
        with respx.mock:
            route = respx.get("https://example.com/jobs").mock(
                side_effect=[
                    httpx.Response(429, headers={"Retry-After": "0"}),
                    httpx.Response(200, json={"ok": True}),
                ]
            )
            payload = await client.get_json("https://example.com/jobs")
    finally:
        await client.aclose()

    assert payload == {"ok": True}
    assert route.call_count == 2


async def test_client_error_is_not_retried(fast_retries: Settings) -> None:
    client = HttpClient(fast_retries)
    try:
        with respx.mock:
            route = respx.get("https://example.com/missing").mock(
                return_value=httpx.Response(404, text="not found")
            )
            with pytest.raises(SourceResponseError):
                await client.get_json("https://example.com/missing")
    finally:
        await client.aclose()

    assert route.call_count == 1


async def test_timeout_becomes_source_unavailable(fast_retries: Settings) -> None:
    client = HttpClient(fast_retries)
    try:
        with respx.mock:
            route = respx.get("https://example.com/slow").mock(
                side_effect=httpx.ConnectTimeout("boom")
            )
            with pytest.raises(SourceUnavailableError):
                await client.get_json("https://example.com/slow")
    finally:
        await client.aclose()

    assert route.call_count == 3


async def test_invalid_json_is_a_response_error(fast_retries: Settings) -> None:
    client = HttpClient(fast_retries)
    try:
        with respx.mock:
            respx.get("https://example.com/html").mock(
                return_value=httpx.Response(200, text="<html>not json</html>")
            )
            with pytest.raises(SourceResponseError):
                await client.get_json("https://example.com/html")
    finally:
        await client.aclose()
