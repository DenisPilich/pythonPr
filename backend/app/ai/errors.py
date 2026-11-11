"""Provider-layer failures that the analysis service can reason about."""

from __future__ import annotations

from typing import Any

from app.core.exceptions import AIProviderError


class AIResponseError(AIProviderError):
    """The provider answered, but not with a valid analysis payload."""

    def __init__(self, detail: str, *, raw: Any = None) -> None:
        super().__init__(detail)
        self.raw = raw
