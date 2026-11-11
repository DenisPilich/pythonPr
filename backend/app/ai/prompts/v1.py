"""Prompt v1: the vacancy/candidate comparison used by every provider.

The prompt is versioned as a file, and the version string is stored on each
`ai_analyses` row. Changing scoring guidance therefore never silently mixes old
and new verdicts.
"""

from __future__ import annotations

from app.ai.types import AnalysisRequest, ProfileSnapshot, VacancySnapshot
from app.utils.text import truncate


PROMPT_VERSION = "v1"
MAX_DESCRIPTION_CHARS = 6000

SYSTEM_PROMPT = """You are a senior technical recruiter and career advisor.
You compare a specific vacancy with a specific candidate profile and decide
whether the candidate should apply.

Rules:
- Judge this candidate, not an imaginary ideal candidate.
- match_score is 0-100: realistic fit including seniority, stack, salary, format and language.
- missing_skills and strong_matches contain concrete technologies from the vacancy, not generic advice.
- red_flags name blockers: seniority mismatch, salary below expectation, language barrier,
  excluded technology, unrealistic requirements, unclear role.
- recommendation: "apply" for 75+, "consider" for 50-74, "skip" below 50.
- reason answers "should I apply and why?" in 2-4 sentences, referencing the profile.
- Never invent skills the candidate did not list. Never repeat the vacancy description.
- Return only JSON matching the requested schema."""


def _format_profile(profile: ProfileSnapshot) -> str:
    target = ", ".join(level.value for level in profile.target_seniority) or "any"
    formats = ", ".join(fmt.value for fmt in profile.work_formats) or "any"
    salary = (
        f"{profile.min_salary_amount} {profile.salary_currency}/month"
        if profile.min_salary_amount
        else "not specified"
    )
    return "\n".join(
        [
            f"Headline: {profile.headline or 'not provided'}",
            f"Desired positions: {', '.join(profile.desired_positions) or 'not specified'}",
            f"Target seniority: {target}",
            f"Skills: {', '.join(profile.skills) or 'not specified'}",
            f"Preferred stack: {', '.join(profile.preferred_stack) or 'not specified'}",
            f"Excluded stack: {', '.join(profile.excluded_stack) or 'none'}",
            f"English level: {profile.english_level.value}",
            f"Salary floor: {salary}",
            f"Preferred locations: {', '.join(profile.preferred_locations) or 'any'}",
            f"Work formats: {formats}",
            f"Notification threshold: {profile.min_match_score}",
        ]
    )


def _format_vacancy(vacancy: VacancySnapshot) -> str:
    technologies = ", ".join(
        f"{tech.name}{'*' if tech.is_required else ''}" for tech in vacancy.technologies
    )
    salary = (
        f"{vacancy.salary_min or 0}-{vacancy.salary_max or 0} {vacancy.salary_currency or ''}"
        if vacancy.salary_min or vacancy.salary_max
        else "not specified"
    )
    normalized = f" (~EUR {vacancy.salary_monthly_eur}/month)" if vacancy.salary_monthly_eur else ""
    return "\n".join(
        [
            f"Title: {vacancy.title}",
            f"Company: {vacancy.company}",
            f"Location: {vacancy.location or 'not specified'}",
            f"Work format: {vacancy.work_format.value}",
            f"Seniority: {vacancy.seniority.value}",
            f"Language: {vacancy.language.value}",
            f"Salary: {salary}{normalized}",
            f"Technologies (* = required): {technologies or 'none extracted'}",
            "Description:",
            truncate(vacancy.description, MAX_DESCRIPTION_CHARS),
        ]
    )


def build_user_prompt(request: AnalysisRequest) -> str:
    prompt = "\n\n".join(
        [
            "CANDIDATE PROFILE",
            _format_profile(request.profile),
            "VACANCY",
            _format_vacancy(request.vacancy),
            "TASK",
            (
                "Compare the vacancy with the candidate and return JSON with match_score, "
                "experience_match, skills_match, missing_skills, strong_matches, red_flags, "
                "recommendation and reason."
            ),
        ]
    )
    if request.repair_note:
        prompt += (
            "\n\nCORRECTION\nYour previous response failed validation: "
            f"{request.repair_note}\nReturn the corrected JSON only."
        )
    return prompt
