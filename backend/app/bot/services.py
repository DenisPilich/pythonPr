"""Bot-side helpers: parsing user input, profile updates, vacancy actions."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.domain.enums import UserVacancyStatus
from app.models import AIAnalysis, UserProfile, UserVacancy, Vacancy
from app.repositories.profiles import ProfileRepository
from app.schemas.profile import ProfilePayload
from app.services.profile import ProfileService


MAX_LIST_ITEMS = 30
_SALARY_RE = re.compile(r"(?P<amount>\d[\d\s]*)\s*(?P<currency>[A-Za-z]{3})?")


@dataclass(frozen=True, slots=True)
class PersonalStats:
    sent: int = 0
    viewed: int = 0
    saved: int = 0
    applied: int = 0
    rejected: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "sent": self.sent,
            "viewed": self.viewed,
            "saved": self.saved,
            "applied": self.applied,
            "rejected": self.rejected,
        }


def parse_list(raw: str) -> list[str]:
    """Comma/newline separated input → clean de-duplicated list."""
    items: list[str] = []
    seen: set[str] = set()
    for chunk in re.split(r"[,\n;]+", raw):
        item = " ".join(chunk.split())
        if not item or len(item) > 64:
            continue
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        items.append(item)
        if len(items) >= MAX_LIST_ITEMS:
            break
    return items


def parse_salary(raw: str) -> tuple[int, str] | None:
    match = _SALARY_RE.search(raw)
    if match is None:
        return None
    amount = int(re.sub(r"\s", "", match.group("amount")))
    if amount <= 0:
        return None
    currency = (match.group("currency") or "EUR").upper()
    if len(currency) != 3 or not currency.isalpha():
        currency = "EUR"
    return amount, currency


def payload_from_profile(profile: UserProfile) -> ProfilePayload:
    return ProfilePayload(
        headline=profile.headline,
        desired_positions=list(profile.desired_positions),
        target_seniority=list(profile.target_seniority),
        skills=list(profile.skills),
        preferred_stack=list(profile.preferred_stack),
        excluded_stack=list(profile.excluded_stack),
        english_level=profile.english_level,
        min_salary_amount=profile.min_salary_amount,
        salary_currency=profile.salary_currency,
        preferred_locations=list(profile.preferred_locations),
        work_formats=list(profile.work_formats),
        min_match_score=profile.min_match_score,
        notifications_enabled=profile.notifications_enabled,
        max_notifications_per_day=profile.max_notifications_per_day,
    )


async def get_profile(session: AsyncSession, user_id: uuid.UUID) -> UserProfile | None:
    return await ProfileRepository(session).get_by_user_id(user_id)


async def ensure_profile(session: AsyncSession, telegram_id: int) -> UserProfile:
    service = ProfileService(session)
    try:
        return await service.get(telegram_id)
    except NotFoundError:
        return await service.create(telegram_id, ProfilePayload())


async def update_profile(
    session: AsyncSession,
    *,
    telegram_id: int,
    user_id: uuid.UUID,
    **changes: object,
) -> UserProfile:
    profile = await ensure_profile(session, telegram_id)
    payload = payload_from_profile(profile).model_copy(update=changes)
    return await ProfileService(session).upsert(telegram_id, payload)


def _status_target(action: str) -> UserVacancyStatus | None:
    return {
        "save": UserVacancyStatus.SAVED,
        "applied": UserVacancyStatus.APPLIED,
        "skip": UserVacancyStatus.REJECTED,
    }.get(action)


def _allowed_transition(current: UserVacancyStatus, target: UserVacancyStatus) -> bool:
    if target is UserVacancyStatus.SAVED:
        return current in {UserVacancyStatus.NEW, UserVacancyStatus.VIEWED}
    if target is UserVacancyStatus.APPLIED:
        return current in {
            UserVacancyStatus.NEW,
            UserVacancyStatus.VIEWED,
            UserVacancyStatus.SAVED,
        }
    if target is UserVacancyStatus.REJECTED:
        return current is not UserVacancyStatus.APPLIED
    return False


async def apply_vacancy_action(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    vacancy_id: uuid.UUID,
    action: str,
) -> UserVacancyStatus | None:
    target = _status_target(action)
    if target is None:
        return None
    vacancy = await session.scalar(
        select(UserVacancy).where(
            UserVacancy.user_id == user_id,
            UserVacancy.vacancy_id == vacancy_id,
        )
    )
    if vacancy is None or not _allowed_transition(vacancy.status, target):
        return None
    now = datetime.now(UTC)
    vacancy.status = target
    if target is UserVacancyStatus.SAVED:
        vacancy.saved_at = now
    elif target is UserVacancyStatus.APPLIED:
        vacancy.applied_at = now
    elif target is UserVacancyStatus.REJECTED:
        vacancy.rejected_at = now
    await session.flush()
    return target


async def list_user_vacancies(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int = 5,
    by_score: bool = False,
) -> list[tuple[UserVacancy, Vacancy, AIAnalysis | None]]:
    order = (
        UserVacancy.match_score.desc().nulls_last() if by_score else UserVacancy.created_at.desc()
    )
    rows = await session.execute(
        select(UserVacancy, Vacancy, AIAnalysis)
        .join(Vacancy, Vacancy.id == UserVacancy.vacancy_id)
        .outerjoin(AIAnalysis, AIAnalysis.id == UserVacancy.ai_analysis_id)
        .where(UserVacancy.user_id == user_id)
        .options(
            selectinload(Vacancy.company),
            selectinload(Vacancy.sources),
        )
        .order_by(order)
        .limit(limit)
    )
    return [(row[0], row[1], row[2]) for row in rows.all()]


async def personal_stats(session: AsyncSession, user_id: uuid.UUID) -> PersonalStats:
    rows = await session.execute(
        select(UserVacancy.status, func.count())
        .where(UserVacancy.user_id == user_id)
        .group_by(UserVacancy.status)
    )
    counts = {status: int(count) for status, count in rows.all()}
    return PersonalStats(
        sent=sum(counts.values()),
        viewed=counts.get(UserVacancyStatus.VIEWED, 0),
        saved=counts.get(UserVacancyStatus.SAVED, 0),
        applied=counts.get(UserVacancyStatus.APPLIED, 0),
        rejected=counts.get(UserVacancyStatus.REJECTED, 0),
    )
