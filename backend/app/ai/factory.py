"""Provider factory: one place that decides mock vs paid model."""

from __future__ import annotations

from app.ai.mock_provider import MockAIProvider
from app.ai.openai_provider import OpenAIProvider
from app.core.config import Settings
from app.ports.ai_provider import AIProvider


def build_ai_provider(settings: Settings) -> AIProvider:
    if settings.ai_provider == "mock":
        return MockAIProvider()
    return OpenAIProvider(settings)


def build_fallback_provider(settings: Settings) -> AIProvider | None:
    """Only used when the primary provider is paid and fallback is enabled."""
    if not settings.ai_fallback_to_mock:
        return None
    if settings.ai_provider == "mock":
        return None
    return MockAIProvider()
