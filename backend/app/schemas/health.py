"""Health schemas shared by the probes and the dashboard status widget."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    checks: dict[str, str] = Field(default_factory=dict)
