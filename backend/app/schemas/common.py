"""Shared API schemas: pagination envelope and enum parameters."""

from __future__ import annotations

from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int = Field(ge=0, description="Total rows matching the filters")
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class JobSortField(StrEnum):
    PUBLISHED_AT = "published_at"
    CREATED_AT = "created_at"
    SALARY = "salary"
    TITLE = "title"
