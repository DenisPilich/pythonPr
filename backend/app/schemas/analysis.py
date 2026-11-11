"""AI analysis response schema."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import Recommendation


class AnalysisRead(BaseModel):
    id: uuid.UUID
    vacancy_id: uuid.UUID
    match_score: int
    experience_match: str
    skills_match: str
    missing_skills: list[str]
    strong_matches: list[str]
    red_flags: list[str]
    recommendation: Recommendation
    reason: str
    provider: str
    model: str
    is_degraded: bool
    prompt_version: str
    created_at: datetime
