"""Deterministic, dependency-free scorer.

Purpose: the whole product must run without a paid API key, and tests need a
provider whose verdict is reproducible. The heuristic is intentionally explicit —
skills coverage, seniority, format, salary and language — so a demo reviews as
"rules, not magic", and every score can be explained in one sentence.
"""

from __future__ import annotations

import time
from decimal import Decimal

from app.ai.schema import AIAnalysisResult
from app.ai.types import AICompletion, AnalysisRequest, TechnologyRef
from app.domain.enums import (
    EnglishLevel,
    Recommendation,
    SeniorityLevel,
    VacancyLanguage,
    WorkFormat,
)
from app.domain.money import to_eur


_SENIORITY_RANK = {
    SeniorityLevel.INTERN: 1,
    SeniorityLevel.JUNIOR: 2,
    SeniorityLevel.MIDDLE: 3,
    SeniorityLevel.SENIOR: 4,
    SeniorityLevel.LEAD: 5,
    SeniorityLevel.UNKNOWN: 0,
}

_HARD_LANGUAGES = {
    VacancyLanguage.DE,
    VacancyLanguage.PL,
    VacancyLanguage.ES,
    VacancyLanguage.UK,
    VacancyLanguage.OTHER,
}


def _technology_terms(technology: TechnologyRef) -> set[str]:
    return {technology.name.casefold(), technology.slug.casefold()}


def _matches(technology: TechnologyRef, profile_terms: set[str]) -> bool:
    return bool(_technology_terms(technology) & profile_terms)


class MockAIProvider:
    name = "mock"
    model = "heuristic-v1"

    async def analyze(self, request: AnalysisRequest) -> AICompletion:
        started = time.perf_counter()
        analysis = self._score(request)
        return AICompletion(
            analysis=analysis,
            provider=self.name,
            model=self.model,
            cost_usd=Decimal("0"),
            latency_ms=max(0, int((time.perf_counter() - started) * 1000)),
            degraded=False,
        )

    def _score(self, request: AnalysisRequest) -> AIAnalysisResult:
        profile = request.profile
        vacancy = request.vacancy

        profile_terms = {term.casefold() for term in (*profile.skills, *profile.preferred_stack)}
        excluded_terms = {term.casefold() for term in profile.excluded_stack}

        technologies = vacancy.technologies
        required = [tech for tech in technologies if tech.is_required] or list(technologies)
        matched_required = [tech for tech in required if _matches(tech, profile_terms)]
        matched_any = [tech for tech in technologies if _matches(tech, profile_terms)]
        missing = [tech.name for tech in required if not _matches(tech, profile_terms)]

        red_flags: list[str] = []
        strong_matches = [tech.name for tech in matched_required]

        if technologies:
            coverage = len(matched_required) / len(required)
            score = 35 + 55 * coverage
        else:
            coverage = None
            score = 55.0

        if vacancy.seniority is not SeniorityLevel.UNKNOWN and profile.target_seniority:
            if vacancy.seniority in profile.target_seniority:
                score += 8
            else:
                score -= 20
                red_flags.append(
                    f"Seniority {vacancy.seniority.value} is outside the target "
                    f"({', '.join(level.value for level in profile.target_seniority)})"
                )

        if profile.work_formats and vacancy.work_format is not WorkFormat.UNKNOWN:
            if vacancy.work_format in profile.work_formats:
                score += 5
            else:
                score -= 20
                red_flags.append(
                    f"Work format {vacancy.work_format.value} is not in the preferred list"
                )

        floor_eur = to_eur(profile.min_salary_amount, profile.salary_currency)
        if vacancy.salary_monthly_eur is not None and floor_eur is not None:
            if vacancy.salary_monthly_eur < floor_eur:
                score -= 25
                red_flags.append(f"Salary is below the floor (~EUR {floor_eur:.0f}/month)")
            elif vacancy.salary_monthly_eur >= floor_eur * Decimal("1.2"):
                score += 5

        excluded_hits = [
            tech.name for tech in technologies if _technology_terms(tech) & excluded_terms
        ]
        if excluded_hits:
            score -= 30
            red_flags.append(f"Excluded stack mentioned: {', '.join(excluded_hits)}")

        if vacancy.language in _HARD_LANGUAGES and profile.english_level in {
            EnglishLevel.A1,
            EnglishLevel.A2,
            EnglishLevel.UNKNOWN,
        }:
            score -= 10
            red_flags.append(
                f"Vacancy is written in {vacancy.language.value}; language may be a barrier"
            )

        final_score = max(0, min(100, round(score)))
        recommendation = (
            Recommendation.APPLY
            if final_score >= 75
            else Recommendation.CONSIDER
            if final_score >= 50
            else Recommendation.SKIP
        )

        if coverage is None:
            skills_match = "No technologies were extracted from the vacancy."
        else:
            skills_match = (
                f"{len(matched_required)} of {len(required)} required technologies match "
                f"({coverage:.0%})."
            )

        target = ", ".join(level.value for level in profile.target_seniority) or "any"
        experience_match = f"Vacancy is {vacancy.seniority.value}; target seniority is {target}."

        reason_parts = [skills_match]
        if missing:
            reason_parts.append(f"Missing: {', '.join(missing[:8])}.")
        if red_flags:
            reason_parts.append(f"Blockers: {'; '.join(red_flags[:3])}.")
        reason_parts.append(
            {
                Recommendation.APPLY: "Strong fit — worth applying.",
                Recommendation.CONSIDER: "Partial fit — apply only if the gaps are acceptable.",
                Recommendation.SKIP: "Weak fit for this profile.",
            }[recommendation]
        )
        if matched_any and not strong_matches:
            strong_matches = [tech.name for tech in matched_any]

        return AIAnalysisResult(
            match_score=final_score,
            experience_match=experience_match,
            skills_match=skills_match,
            missing_skills=missing[:10],
            strong_matches=strong_matches[:10],
            red_flags=red_flags[:10],
            recommendation=recommendation,
            reason=" ".join(reason_parts)[:2000],
        )

    async def aclose(self) -> None:
        return None
