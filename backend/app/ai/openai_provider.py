"""OpenAI-compatible provider using JSON-schema structured outputs.

Uses plain `httpx` instead of the official SDK: one POST with a JSON schema is the
whole integration, and the HTTP client is already a first-class dependency of the
project. `OPENAI_BASE_URL` makes it work with proxies and local OpenAI-compatible
servers.
"""

from __future__ import annotations

import asyncio
import json
import time
from decimal import Decimal
from typing import Any

import httpx
import structlog
from pydantic import ValidationError

from app.ai.errors import AIResponseError
from app.ai.prompts.v1 import SYSTEM_PROMPT, build_user_prompt
from app.ai.schema import RESPONSE_SCHEMA, AIAnalysisResult
from app.ai.types import AICompletion, AnalysisRequest
from app.core.config import Settings
from app.core.exceptions import AIProviderError, ConfigurationError


logger = structlog.get_logger(__name__)

DEFAULT_BASE_URL = "https://api.openai.com/v1"

# USD per million tokens. Unknown models cost 0 in accounting; the budget guard is
# then blind, which is logged as a warning.
_PRICES: dict[str, tuple[Decimal, Decimal]] = {
    "gpt-4o-mini": (Decimal("0.15"), Decimal("0.60")),
    "gpt-4o": (Decimal("2.50"), Decimal("10.00")),
    "gpt-4.1-mini": (Decimal("0.40"), Decimal("1.60")),
}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> Decimal:
    prompt_price, completion_price = _PRICES.get(model, (Decimal("0"), Decimal("0")))
    total = (
        Decimal(prompt_tokens) * prompt_price + Decimal(completion_tokens) * completion_price
    ) / Decimal(1_000_000)
    return total.quantize(Decimal("0.000001"))


class OpenAIProvider:
    name = "openai"

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        if settings.openai_api_key is None:
            raise ConfigurationError("AI_PROVIDER=openai requires OPENAI_API_KEY to be set")
        self._settings = settings
        self._model = settings.ai_model
        self._base_url = (settings.openai_base_url or DEFAULT_BASE_URL).rstrip("/")
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(settings.ai_timeout_seconds)
        )
        self._headers = {
            "Authorization": f"Bearer {settings.openai_api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }

    async def analyze(self, request: AnalysisRequest) -> AICompletion:
        started = time.perf_counter()
        payload = {
            "model": self._model,
            "temperature": self._settings.ai_temperature,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(request)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "vacancy_analysis",
                    "strict": True,
                    "schema": RESPONSE_SCHEMA,
                },
            },
        }

        last_error: Exception | None = None
        for attempt in range(self._settings.ai_max_retries + 1):
            try:
                response = await self._client.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                    headers=self._headers,
                )
            except httpx.HTTPError as exc:
                last_error = exc
            else:
                if response.status_code == 200:
                    return self._parse(response, started)
                if response.status_code in {429, 500, 502, 503, 504}:
                    last_error = AIProviderError(f"OpenAI returned {response.status_code}")
                else:
                    raise AIProviderError(
                        f"OpenAI returned {response.status_code}: {response.text[:300]}"
                    )
            if attempt < self._settings.ai_max_retries:
                await asyncio.sleep(0.5 * (attempt + 1))

        raise AIProviderError(f"OpenAI request failed after retries: {last_error}") from last_error

    def _parse(self, response: httpx.Response, started: float) -> AICompletion:
        data: dict[str, Any] = {}
        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise AIResponseError("Malformed chat-completions response", raw=data) from exc

        if isinstance(content, dict):
            decoded: Any = content
        else:
            try:
                decoded = json.loads(content)
            except (TypeError, json.JSONDecodeError) as exc:
                raise AIResponseError(
                    f"Model returned non-JSON content: {str(content)[:200]}"
                ) from exc

        try:
            analysis = AIAnalysisResult.model_validate(decoded)
        except ValidationError as exc:
            raise AIResponseError(
                f"Model output failed schema validation: {exc.errors()[:3]}", raw=decoded
            ) from exc

        usage = data.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        return AICompletion(
            analysis=analysis,
            provider=self.name,
            model=str(data.get("model") or self._model),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=estimate_cost(self._model, prompt_tokens, completion_tokens),
            latency_ms=max(0, int((time.perf_counter() - started) * 1000)),
            raw_response=data,
        )

    async def aclose(self) -> None:
        await self._client.aclose()
