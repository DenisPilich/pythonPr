"""Service metadata — a cheap smoke-test endpoint and a version source for the UI."""

from __future__ import annotations

from pydantic import BaseModel


class MetaResponse(BaseModel):
    name: str
    version: str
    environment: str
    api_prefix: str
    docs_url: str
