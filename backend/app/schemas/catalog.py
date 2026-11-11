"""Company and technology read schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.domain.enums import TechnologyCategory


class CompanyRead(BaseModel):
    id: uuid.UUID
    name: str
    normalized_name: str
    website: str | None
    logo_url: str | None
    vacancy_count: int = Field(ge=0)


class TechnologyRead(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    category: TechnologyCategory
    aliases: list[str]
    vacancy_count: int = Field(ge=0)
