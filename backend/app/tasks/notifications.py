"""Notification task: enqueue newly matched vacancies and drain the pending queue."""

from __future__ import annotations

from app.core.config import Settings
from app.db.session import Database
from app.ports.vacancy_source import Notifier
from app.services.notification import NotificationService
from app.tasks.celery_app import celery_app
from app.tasks.runtime import get_runtime, run_async


async def send_notifications_async(
    *,
    database: Database,
    notifier: Notifier,
    settings: Settings,
) -> dict[str, int]:
    async with database.session() as session:
        service = NotificationService(session, notifier)
        report = await service.run_once(
            enqueue_limit=settings.notification_batch_size * 5,
            send_limit=settings.notification_batch_size,
        )
    return {
        "enqueued": report.enqueued,
        "sent": report.sent,
        "failed": report.failed,
    }


@celery_app.task(
    name="app.tasks.notifications.send_pending_notifications",
    soft_time_limit=240,
)
def send_pending_notifications() -> dict[str, int]:
    runtime = get_runtime()
    return run_async(
        send_notifications_async(
            database=runtime.database,
            notifier=runtime.notifier,
            settings=runtime.settings,
        )
    )
