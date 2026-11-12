"""Notification persistence and dispatch queries.

Enqueue is idempotent through the `(user_id, vacancy_id, channel)` unique index;
dispatch claims rows with `FOR UPDATE SKIP LOCKED` so several workers can drain
the queue without sending the same message twice.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import exists, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.enums import (
    NotificationChannel,
    NotificationStatus,
    UserVacancyStatus,
)
from app.models import (
    AIAnalysis,
    Notification,
    User,
    UserProfile,
    UserVacancy,
    Vacancy,
    VacancySource,
    VacancyTechnology,
)


@dataclass(frozen=True, slots=True)
class NotificationContext:
    notification: Notification
    user: User
    profile: UserProfile
    vacancy: Vacancy
    user_vacancy: UserVacancy
    analysis: AIAnalysis | None


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue_matches(self, *, limit: int = 100) -> int:
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        sent_today = (
            select(func.count(Notification.id))
            .where(
                Notification.user_id == User.id,
                Notification.status == NotificationStatus.SENT,
                Notification.sent_at >= today,
            )
            .correlate(User)
            .scalar_subquery()
        )

        statement = (
            select(
                UserVacancy.user_id,
                UserVacancy.vacancy_id,
                UserVacancy.match_score,
            )
            .join(User, User.id == UserVacancy.user_id)
            .join(UserProfile, UserProfile.user_id == User.id)
            .where(
                UserVacancy.status == UserVacancyStatus.NEW,
                UserVacancy.is_notified.is_(False),
                UserVacancy.match_score.is_not(None),
                UserVacancy.match_score >= UserProfile.min_match_score,
                User.is_active.is_(True),
                UserProfile.notifications_enabled.is_(True),
                UserProfile.max_notifications_per_day > sent_today,
                ~exists().where(
                    Notification.user_id == UserVacancy.user_id,
                    Notification.vacancy_id == UserVacancy.vacancy_id,
                    Notification.channel == NotificationChannel.TELEGRAM,
                ),
            )
            .order_by(UserVacancy.match_score.desc(), UserVacancy.created_at.asc())
            .limit(limit)
        )
        rows = (await self._session.execute(statement)).all()
        if not rows:
            return 0

        values = [
            {
                "user_id": user_id,
                "vacancy_id": vacancy_id,
                "channel": NotificationChannel.TELEGRAM,
                "status": NotificationStatus.PENDING,
            }
            for user_id, vacancy_id, _score in rows
        ]
        await self._session.execute(
            pg_insert(Notification)
            .values(values)
            .on_conflict_do_nothing(
                index_elements=[
                    Notification.user_id,
                    Notification.vacancy_id,
                    Notification.channel,
                ]
            )
        )
        return len(values)

    async def claim_pending(self, *, limit: int = 20) -> list[Notification]:
        statement = (
            select(Notification)
            .where(Notification.status == NotificationStatus.PENDING)
            .order_by(Notification.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list((await self._session.scalars(statement)).all())

    async def load_context(self, notification: Notification) -> NotificationContext | None:
        user = await self._session.get(User, notification.user_id)
        profile = await self._session.scalar(
            select(UserProfile).where(UserProfile.user_id == notification.user_id)
        )
        vacancy = await self._session.scalar(
            select(Vacancy)
            .where(Vacancy.id == notification.vacancy_id)
            .options(
                selectinload(Vacancy.company),
                selectinload(Vacancy.sources).selectinload(VacancySource.source),
                selectinload(Vacancy.technologies).selectinload(VacancyTechnology.technology),
            )
        )
        user_vacancy = await self._session.scalar(
            select(UserVacancy)
            .where(
                UserVacancy.user_id == notification.user_id,
                UserVacancy.vacancy_id == notification.vacancy_id,
            )
            .options(selectinload(UserVacancy.ai_analysis))
        )
        if user is None or profile is None or vacancy is None or user_vacancy is None:
            return None
        return NotificationContext(
            notification=notification,
            user=user,
            profile=profile,
            vacancy=vacancy,
            user_vacancy=user_vacancy,
            analysis=user_vacancy.ai_analysis,
        )

    async def mark_sent(self, notification: Notification, *, message_id: int) -> None:
        now = datetime.now(UTC)
        notification.status = NotificationStatus.SENT
        notification.telegram_message_id = message_id
        notification.sent_at = now
        notification.error = None
        await self._session.execute(
            update(UserVacancy)
            .where(
                UserVacancy.user_id == notification.user_id,
                UserVacancy.vacancy_id == notification.vacancy_id,
            )
            .values(is_notified=True, notified_at=now)
        )
        await self._session.flush()

    async def mark_failed(self, notification: Notification, *, error: str) -> None:
        notification.status = NotificationStatus.FAILED
        notification.error = error[:2000]
        await self._session.flush()

    async def count_sent_for_user(self, user_id: uuid.UUID, *, days: int = 1) -> int:
        since = datetime.now(UTC) - timedelta(days=days)
        total = await self._session.scalar(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.status == NotificationStatus.SENT,
                Notification.sent_at >= since,
            )
        )
        return int(total or 0)


def salary_payload(vacancy: Vacancy) -> dict[str, Any]:
    return {
        "minimum": vacancy.salary_min,
        "maximum": vacancy.salary_max,
        "currency": vacancy.salary_currency,
        "period": vacancy.salary_period,
        "monthly_eur": vacancy.salary_monthly_eur,
    }
