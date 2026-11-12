"""User history schemas (dashboard needs vacancy + per-user status together)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enums import UserVacancyStatus
from app.schemas.common import Page
from app.schemas.jobs import JobListItem


class HistoryItem(BaseModel):
    job: JobListItem
    status: UserVacancyStatus
    match_score: int | None
    notified_at: datetime | None
    created_at: datetime


class HistoryCounts(BaseModel):
    new: int = 0
    viewed: int = 0
    saved: int = 0
    applied: int = 0
    rejected: int = 0
    total: int = 0


class HistoryPage(Page[HistoryItem]):
    counts: HistoryCounts = Field(default_factory=HistoryCounts)
