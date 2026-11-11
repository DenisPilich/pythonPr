"""Seniority detection from the title, then the description, then stated years."""

from __future__ import annotations

import re

from app.domain.enums import SeniorityLevel


_PATTERNS: tuple[tuple[SeniorityLevel, re.Pattern[str]], ...] = (
    (
        SeniorityLevel.INTERN,
        re.compile(r"\b(intern|internship|trainee|стаж[её]р\w*|практикант\w*)\b", re.I),
    ),
    (
        SeniorityLevel.LEAD,
        re.compile(
            r"\b(lead|principal|staff engineer|head of|tech lead|team lead|руководител\w*|ведущий)\b",
            re.I,
        ),
    ),
    (SeniorityLevel.SENIOR, re.compile(r"\b(senior|sr\.?|сеньор\w*|старший)\b", re.I)),
    (
        SeniorityLevel.JUNIOR,
        re.compile(r"\b(junior|jr\.?|джуниор\w*|младший|начинающий)\b", re.I),
    ),
    (SeniorityLevel.MIDDLE, re.compile(r"\b(middle|mid[- ]level|мидл\w*)\b", re.I)),
)
_YEARS_RE = re.compile(r"(\d{1,2})\s*(?:\+|plus)?\s*(?:years?|yrs?|лет|года|год)\b", re.IGNORECASE)


def _first_match(text: str) -> SeniorityLevel | None:
    for level, pattern in _PATTERNS:
        if pattern.search(text):
            return level
    return None


def detect_seniority(title: str, description: str = "") -> SeniorityLevel:
    """Title wins over description; years of experience are the last resort."""
    level = _first_match(title)
    if level is not None:
        return level

    level = _first_match(description[:1500])
    if level is not None:
        return level

    years = [int(value) for value in _YEARS_RE.findall(description[:3000])]
    if years:
        minimum = min(years)
        if minimum <= 1:
            return SeniorityLevel.JUNIOR
        if minimum <= 4:
            return SeniorityLevel.MIDDLE
        return SeniorityLevel.SENIOR
    return SeniorityLevel.UNKNOWN
