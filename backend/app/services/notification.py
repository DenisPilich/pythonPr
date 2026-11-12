"""Notification use case: enqueue matches, dispatch them, record the outcome.

For stage 5 the delivery channel is a logging notifier; stage 6 swaps in the
Telegram implementation without touching this service.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import Recommendation
from app.ports.vacancy_source import Notifier
from app.repositories.notifications import (
    NotificationContext,
    NotificationRepository,
    salary_payload,
)
from app.services.notification_format import format_salary, render_vacancy_notification


logger = structlog.get_logger(__name__)

MAX_MESSAGE_LENGTH = 4000


@dataclass(frozen=True, slots=True)
class NotificationReport:
    enqueued: int
    sent: int
    failed: int


class LoggingNotifier:
    """No-op delivery used until the Telegram bot is wired in stage 6."""

    name = "log"

    def __init__(self) -> None:
        self._counter = 0

    async def send_vacancy(self, chat_id: int, text: str) -> int:
        self._counter += 1
        logger.info(
            "notification_preview",
            chat_id=chat_id,
            message_id=self._counter,
            preview=text[:240],
        )
        return self._counter


class NotificationService:
    def __init__(self, session: AsyncSession, notifier: Notifier) -> None:
        self._session = session
        self._repository = NotificationRepository(session)
        self._notifier = notifier

    async def run_once(
        self, *, enqueue_limit: int = 100, send_limit: int = 20
    ) -> NotificationReport:
        enqueued = await self._repository.enqueue_matches(limit=enqueue_limit)
        pending = await self._repository.claim_pending(limit=send_limit)
        sent = failed = 0

        for notification in pending:
            context = await self._repository.load_context(notification)
            if context is None:
                await self._repository.mark_failed(
                    notification, error="missing user, profile, vacancy or tracking row"
                )
                failed += 1
                continue

            text = self._render(context)
            try:
                message_id = await self._notifier.send_vacancy(context.user.telegram_id, text)
            except Exception as exc:
                logger.exception(
                    "notification_delivery_failed",
                    notification_id=str(notification.id),
                    user_id=str(notification.user_id),
                    error=type(exc).__name__,
                )
                await self._repository.mark_failed(
                    notification, error=f"{type(exc).__name__}: {exc}"
                )
                failed += 1
            else:
                await self._repository.mark_sent(notification, message_id=message_id)
                sent += 1

        if enqueued or sent or failed:
            logger.info(
                "notifications_dispatched",
                enqueued=enqueued,
                sent=sent,
                failed=failed,
            )
        return NotificationReport(enqueued=enqueued, sent=sent, failed=failed)

    @staticmethod
    def _render(context: NotificationContext) -> str:
        vacancy = context.vacancy
        analysis = context.analysis
        references = sorted(vacancy.sources, key=lambda ref: ref.first_seen_at)
        url = references[0].url if references else ""

        score = analysis.match_score if analysis else (context.user_vacancy.match_score or 0)
        recommendation = analysis.recommendation if analysis else Recommendation.CONSIDER
        text = render_vacancy_notification(
            title=vacancy.title,
            company=vacancy.company.name,
            location=vacancy.location_raw,
            salary=format_salary(**salary_payload(vacancy)),
            seniority=vacancy.seniority.value,
            match_score=score,
            strong_matches=list(analysis.strong_matches) if analysis else [],
            missing_skills=list(analysis.missing_skills) if analysis else [],
            recommendation=recommendation,
            url=url,
        )
        return text[:MAX_MESSAGE_LENGTH]
