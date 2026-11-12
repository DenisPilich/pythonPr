"""Celery application: queues, retry semantics, beat schedule.

One beat replica only schedules; workers do the I/O. `acks_late` plus
`reject_on_worker_lost` means a killed worker does not silently drop a task.
"""

from __future__ import annotations

from datetime import timedelta

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init

from app.core.config import get_settings
from app.tasks.runtime import reset_runtime


settings = get_settings()

celery_app = Celery(
    "ai_job_radar",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.collection",
        "app.tasks.analysis",
        "app.tasks.notifications",
        "app.tasks.maintenance",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=200,
    broker_transport_options={"visibility_timeout": 3600},
    task_default_queue="default",
    task_routes={
        "app.tasks.collection.*": {"queue": "collect"},
        "app.tasks.analysis.*": {"queue": "analyze"},
        "app.tasks.notifications.*": {"queue": "notify"},
    },
    beat_schedule={
        "collect-all-sources": {
            "task": "app.tasks.collection.collect_all_sources",
            "schedule": timedelta(minutes=settings.collect_interval_minutes),
        },
        "analyze-new-vacancies": {
            "task": "app.tasks.analysis.analyze_new_vacancies",
            "schedule": timedelta(minutes=settings.analyze_interval_minutes),
        },
        "send-pending-notifications": {
            "task": "app.tasks.notifications.send_pending_notifications",
            "schedule": timedelta(minutes=settings.notify_interval_minutes),
        },
        "refresh-stats-cache": {
            "task": "app.tasks.maintenance.refresh_stats_cache",
            "schedule": timedelta(minutes=settings.stats_interval_minutes),
        },
        "deactivate-stale-vacancies": {
            "task": "app.tasks.maintenance.deactivate_stale_vacancies",
            "schedule": crontab(minute=0, hour=3),
        },
    },
)


@worker_process_init.connect
def _reset_worker_runtime(**_kwargs: object) -> None:
    """Child processes must not inherit a loop/engine created before fork."""
    reset_runtime()
