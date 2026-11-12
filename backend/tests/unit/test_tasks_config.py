from __future__ import annotations

from app.tasks import analysis, collection, maintenance, notifications  # noqa: F401
from app.tasks.celery_app import celery_app


def test_all_pipeline_tasks_are_registered() -> None:
    registered = {name for name in celery_app.tasks if name.startswith("app.tasks.")}

    assert {
        "app.tasks.collection.collect_source",
        "app.tasks.collection.collect_all_sources",
        "app.tasks.analysis.analyze_vacancy",
        "app.tasks.analysis.analyze_new_vacancies",
        "app.tasks.notifications.send_pending_notifications",
        "app.tasks.maintenance.refresh_stats_cache",
        "app.tasks.maintenance.deactivate_stale_vacancies",
    } <= registered


def test_beat_schedule_covers_the_pipeline() -> None:
    schedule = celery_app.conf.beat_schedule
    tasks = {entry["task"] for entry in schedule.values()}

    assert tasks == {
        "app.tasks.collection.collect_all_sources",
        "app.tasks.analysis.analyze_new_vacancies",
        "app.tasks.notifications.send_pending_notifications",
        "app.tasks.maintenance.refresh_stats_cache",
        "app.tasks.maintenance.deactivate_stale_vacancies",
    }


def test_tasks_are_routed_to_dedicated_queues() -> None:
    routes = celery_app.conf.task_routes

    assert routes["app.tasks.collection.*"]["queue"] == "collect"
    assert routes["app.tasks.analysis.*"]["queue"] == "analyze"
    assert routes["app.tasks.notifications.*"]["queue"] == "notify"


def test_delivery_semantics() -> None:
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert celery_app.conf.timezone == "UTC"
