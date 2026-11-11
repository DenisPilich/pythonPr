"""AI provider port."""

from __future__ import annotations

from typing import Protocol

from app.ai.types import AICompletion, AnalysisRequest


class AIProvider(Protocol):
    name: str

    async def analyze(self, request: AnalysisRequest) -> AICompletion: ...

    async def aclose(self) -> None: ...
