"""Structured analysis contract — the JSON every provider must produce.

`extra="forbid"` is intentional: a model that invents fields is a model whose
output we cannot trust, and structured outputs make the failure visible instead
of silently dropping data.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import Recommendation


class AIAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_score: int = Field(ge=0, le=100)
    experience_match: str = Field(min_length=1, max_length=1000)
    skills_match: str = Field(min_length=1, max_length=1000)
    missing_skills: list[str] = Field(default_factory=list, max_length=30)
    strong_matches: list[str] = Field(default_factory=list, max_length=30)
    red_flags: list[str] = Field(default_factory=list, max_length=30)
    recommendation: Recommendation
    reason: str = Field(min_length=1, max_length=2000)


# Strict JSON schema for OpenAI-compatible structured outputs. Kept hand-written
# because Pydantic emits constraints (`minimum`, `maximum`) that strict mode
# rejects; range validation happens in `AIAnalysisResult` after parsing.
RESPONSE_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "match_score",
        "experience_match",
        "skills_match",
        "missing_skills",
        "strong_matches",
        "red_flags",
        "recommendation",
        "reason",
    ],
    "properties": {
        "match_score": {
            "type": "integer",
            "description": "0-100 fit score for this candidate",
        },
        "experience_match": {"type": "string"},
        "skills_match": {"type": "string"},
        "missing_skills": {"type": "array", "items": {"type": "string"}},
        "strong_matches": {"type": "array", "items": {"type": "string"}},
        "red_flags": {"type": "array", "items": {"type": "string"}},
        "recommendation": {
            "type": "string",
            "enum": ["apply", "consider", "skip"],
        },
        "reason": {"type": "string"},
    },
}


def parse_analysis_payload(payload: object) -> AIAnalysisResult:
    """Validate a decoded JSON object; raises `pydantic.ValidationError`."""
    return AIAnalysisResult.model_validate(payload)
