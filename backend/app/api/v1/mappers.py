"""ORM → API schema mapping.

Kept out of endpoints so response shaping is testable and the routers stay about
HTTP concerns. Every relationship used here is eager-loaded by the repository.
"""

from __future__ import annotations

from app.models import AIAnalysis, UserProfile, Vacancy
from app.schemas.analysis import AnalysisRead
from app.schemas.jobs import CompanyBrief, JobDetail, JobListItem, SourceRef, TechnologyBrief
from app.schemas.profile import ProfileRead


def job_to_list_item(vacancy: Vacancy) -> JobListItem:
    references = sorted(vacancy.sources, key=lambda ref: ref.first_seen_at)
    primary = references[0] if references else None
    technologies = sorted(
        vacancy.technologies, key=lambda link: (-link.mentions, link.technology.slug)
    )
    return JobListItem(
        id=vacancy.id,
        title=vacancy.title,
        company=CompanyBrief.model_validate(vacancy.company),
        url=primary.url if primary else "",
        location_raw=vacancy.location_raw,
        city=vacancy.city,
        country_code=vacancy.country_code,
        work_format=vacancy.work_format,
        seniority=vacancy.seniority,
        language=vacancy.language,
        salary_min=vacancy.salary_min,
        salary_max=vacancy.salary_max,
        salary_currency=vacancy.salary_currency,
        salary_period=vacancy.salary_period,
        salary_monthly_eur=vacancy.salary_monthly_eur,
        published_at=vacancy.published_at,
        first_seen_at=vacancy.first_seen_at,
        technologies=[
            TechnologyBrief(
                slug=link.technology.slug,
                name=link.technology.name,
                category=link.technology.category,
            )
            for link in technologies
        ],
        sources=[
            SourceRef(source=ref.source.code, name=ref.source.name, url=ref.url)
            for ref in references
        ],
    )


def job_to_detail(vacancy: Vacancy) -> JobDetail:
    base = job_to_list_item(vacancy)
    return JobDetail(
        **base.model_dump(),
        description=vacancy.description_clean,
        created_at=vacancy.created_at,
        updated_at=vacancy.updated_at,
    )


def profile_to_read(profile: UserProfile, telegram_id: int) -> ProfileRead:
    return ProfileRead(
        id=profile.id,
        telegram_id=telegram_id,
        headline=profile.headline,
        desired_positions=profile.desired_positions,
        target_seniority=profile.target_seniority,
        skills=profile.skills,
        preferred_stack=profile.preferred_stack,
        excluded_stack=profile.excluded_stack,
        english_level=profile.english_level,
        min_salary_amount=profile.min_salary_amount,
        salary_currency=profile.salary_currency,
        preferred_locations=profile.preferred_locations,
        work_formats=profile.work_formats,
        min_match_score=profile.min_match_score,
        notifications_enabled=profile.notifications_enabled,
        max_notifications_per_day=profile.max_notifications_per_day,
        profile_hash=profile.profile_hash,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def analysis_to_read(analysis: AIAnalysis) -> AnalysisRead:
    return AnalysisRead(
        id=analysis.id,
        vacancy_id=analysis.vacancy_id,
        match_score=analysis.match_score,
        experience_match=analysis.experience_match,
        skills_match=analysis.skills_match,
        missing_skills=analysis.missing_skills,
        strong_matches=analysis.strong_matches,
        red_flags=analysis.red_flags,
        recommendation=analysis.recommendation,
        reason=analysis.reason,
        provider=analysis.provider,
        model=analysis.model,
        is_degraded=analysis.is_degraded,
        prompt_version=analysis.prompt_version,
        created_at=analysis.created_at,
    )
