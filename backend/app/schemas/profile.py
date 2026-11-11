"""Profile request/response schemas.

List fields are cleaned and de-duplicated case-insensitively: a user who types
"Python, python, PYTHON" should not get four entries in the prompt or the UI.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import EnglishLevel, SeniorityLevel, WorkFormat


_LIST_FIELDS = (
    "desired_positions",
    "skills",
    "preferred_stack",
    "excluded_stack",
    "preferred_locations",
)

PROFILE_EXAMPLE: dict[str, Any] = {
    "headline": "Python backend developer, 3 years",
    "desired_positions": ["Python Backend Developer", "Backend Engineer"],
    "target_seniority": ["junior", "middle"],
    "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
    "preferred_stack": ["FastAPI", "PostgreSQL", "Redis"],
    "excluded_stack": ["PHP"],
    "english_level": "b2",
    "min_salary_amount": 2500,
    "salary_currency": "EUR",
    "preferred_locations": ["Germany", "Poland", "Remote"],
    "work_formats": ["remote", "hybrid"],
    "min_match_score": 75,
    "notifications_enabled": True,
    "max_notifications_per_day": 10,
}


class ProfilePayload(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={"example": PROFILE_EXAMPLE},
    )

    headline: str | None = Field(default=None, max_length=160)
    desired_positions: list[str] = Field(default_factory=list, max_length=10)
    target_seniority: list[SeniorityLevel] = Field(default_factory=list, max_length=6)
    skills: list[str] = Field(default_factory=list, max_length=100)
    preferred_stack: list[str] = Field(default_factory=list, max_length=30)
    excluded_stack: list[str] = Field(default_factory=list, max_length=30)
    english_level: EnglishLevel = EnglishLevel.UNKNOWN
    min_salary_amount: int | None = Field(default=None, ge=0, le=10_000_000)
    salary_currency: str = Field(default="EUR", pattern=r"^[A-Za-z]{3}$")
    preferred_locations: list[str] = Field(default_factory=list, max_length=20)
    work_formats: list[WorkFormat] = Field(default_factory=list, max_length=4)
    min_match_score: int = Field(default=70, ge=0, le=100)
    notifications_enabled: bool = True
    max_notifications_per_day: int = Field(default=10, ge=0, le=100)

    @field_validator("salary_currency")
    @classmethod
    def _uppercase_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator(*_LIST_FIELDS)
    @classmethod
    def _clean_list(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw in values:
            item = " ".join(raw.split())
            if not item:
                continue
            if len(item) > 64:
                raise ValueError("list items must be at most 64 characters")
            key = item.casefold()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(item)
        return cleaned

    @field_validator("target_seniority", "work_formats")
    @classmethod
    def _deduplicate_enums(cls, values: list[Any]) -> list[Any]:
        return list(dict.fromkeys(values))


class ProfileRead(BaseModel):
    id: uuid.UUID
    telegram_id: int
    headline: str | None
    desired_positions: list[str]
    target_seniority: list[SeniorityLevel]
    skills: list[str]
    preferred_stack: list[str]
    excluded_stack: list[str]
    english_level: EnglishLevel
    min_salary_amount: int | None
    salary_currency: str
    preferred_locations: list[str]
    work_formats: list[WorkFormat]
    min_match_score: int
    notifications_enabled: bool
    max_notifications_per_day: int
    profile_hash: str
    created_at: datetime
    updated_at: datetime
