from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.mock_provider import MockAIProvider
from app.core.config import Settings
from app.domain.enums import (
    CollectorRunStatus,
    NotificationStatus,
    SourceKind,
    UserVacancyStatus,
)
from app.models import CollectorRun, Notification, Source, UserVacancy, Vacancy
from app.ports.vacancy_source import NotificationMessage
from app.tasks.analysis import analyze_vacancy_async, pending_analysis_pairs
from app.tasks.collection import collect_source_async
from app.tasks.locks import LockNotAcquiredError, redis_lock
from app.tasks.maintenance import deactivate_stale_async
from app.tasks.notifications import send_notifications_async
from tests.integration.conftest import StubDatabase
from tests.integration.test_analysis_service import create_profile, create_vacancy


pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


class RecordingNotifier:
    name = "recording"

    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []

    async def send_vacancy(self, message: NotificationMessage) -> int:
        self.messages.append((message.chat_id, message.text))
        return len(self.messages)


def load_json(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


async def create_hh_source(session: AsyncSession) -> Source:
    source = Source(
        code="hh",
        name="hh.ru",
        kind=SourceKind.JSON_API,
        base_url="https://api.hh.ru",
        rate_limit_per_min=10_000,
        config={"per_page": 20, "max_pages": 1},
    )
    session.add(source)
    await session.flush()
    return source


async def test_redis_lock_is_exclusive(fake_redis: Any) -> None:
    async with redis_lock(fake_redis, "lock:test", ttl_seconds=30):
        with pytest.raises(LockNotAcquiredError):
            async with redis_lock(fake_redis, "lock:test", ttl_seconds=30):
                pass
    assert await fake_redis.get("lock:test") is None


@respx.mock
async def test_collect_source_records_run(
    db_session: AsyncSession,
    stub_database: StubDatabase,
    fake_redis: Any,
    settings: Settings,
    taxonomy_rows: None,
) -> None:
    await create_hh_source(db_session)
    respx.get("https://api.hh.ru/vacancies").mock(
        return_value=httpx.Response(200, json=load_json("hh_page.json"))
    )

    report = await collect_source_async(
        "hh",
        database=stub_database,
        redis=fake_redis,
        settings=settings,
        max_pages=1,
    )

    assert report["status"] == "partial"
    assert report["created"] == 1
    assert report["skipped"] == 1
    assert await db_session.scalar(select(func.count()).select_from(Vacancy)) == 1
    run = await db_session.scalar(select(CollectorRun))
    assert run is not None
    assert run.status is CollectorRunStatus.PARTIAL
    assert run.items_created == 1


async def test_collect_source_skips_when_locked(
    db_session: AsyncSession,
    stub_database: StubDatabase,
    fake_redis: Any,
    settings: Settings,
) -> None:
    await create_hh_source(db_session)
    await fake_redis.set("lock:collect:hh", "another-worker")

    report = await collect_source_async(
        "hh",
        database=stub_database,
        redis=fake_redis,
        settings=settings,
        max_pages=1,
    )

    assert report == {"source": "hh", "status": "locked"}
    assert await db_session.scalar(select(func.count()).select_from(CollectorRun)) == 0


async def test_pending_pairs_disappear_after_analysis(
    db_session: AsyncSession,
    stub_database: StubDatabase,
    settings: Settings,
    taxonomy_rows: None,
) -> None:
    user, _ = await create_profile(db_session)
    vacancy = await create_vacancy(db_session)

    pairs = await pending_analysis_pairs(db_session, limit=10, lookback_days=365)
    assert (vacancy.id, user.id) in pairs

    result = await analyze_vacancy_async(
        vacancy.id,
        user.id,
        database=stub_database,
        provider=MockAIProvider(),
        settings=settings,
    )

    assert result["score"] >= 75
    assert result["cached"] is False
    remaining = await pending_analysis_pairs(db_session, limit=10, lookback_days=365)
    assert (vacancy.id, user.id) not in remaining


async def test_notifications_are_enqueued_and_sent(
    db_session: AsyncSession,
    stub_database: StubDatabase,
    settings: Settings,
    taxonomy_rows: None,
) -> None:
    user, _ = await create_profile(db_session)
    vacancy = await create_vacancy(db_session)
    db_session.add(
        UserVacancy(
            user_id=user.id,
            vacancy_id=vacancy.id,
            status=UserVacancyStatus.NEW,
            match_score=90,
        )
    )
    await db_session.flush()
    notifier = RecordingNotifier()

    report = await send_notifications_async(
        database=stub_database, notifier=notifier, settings=settings
    )

    assert report == {"enqueued": 1, "sent": 1, "failed": 0}
    assert len(notifier.messages) == 1
    chat_id, text = notifier.messages[0]
    assert chat_id == user.telegram_id
    assert "Senior Python Developer" in text
    assert "Match: <b>90%</b>" in text

    notification = await db_session.scalar(select(Notification))
    assert notification is not None
    assert notification.status is NotificationStatus.SENT
    assert notification.telegram_message_id == 1

    tracked = await db_session.scalar(
        select(UserVacancy).where(
            UserVacancy.user_id == user.id, UserVacancy.vacancy_id == vacancy.id
        )
    )
    assert tracked is not None and tracked.is_notified is True

    second = await send_notifications_async(
        database=stub_database, notifier=notifier, settings=settings
    )
    assert second == {"enqueued": 0, "sent": 0, "failed": 0}


async def test_daily_quota_blocks_enqueue(
    db_session: AsyncSession,
    stub_database: StubDatabase,
    settings: Settings,
    taxonomy_rows: None,
) -> None:
    user, _ = await create_profile(db_session, max_notifications_per_day=0)
    vacancy = await create_vacancy(db_session)
    db_session.add(
        UserVacancy(
            user_id=user.id,
            vacancy_id=vacancy.id,
            status=UserVacancyStatus.NEW,
            match_score=95,
        )
    )
    await db_session.flush()

    report = await send_notifications_async(
        database=stub_database, notifier=RecordingNotifier(), settings=settings
    )

    assert report["enqueued"] == 0


async def test_deactivate_stale_vacancies(
    db_session: AsyncSession,
    stub_database: StubDatabase,
    taxonomy_rows: None,
) -> None:
    vacancy = await create_vacancy(db_session)
    vacancy.last_seen_at = datetime.now(UTC) - timedelta(days=90)
    await db_session.flush()

    deactivated = await deactivate_stale_async(stub_database, days=60)

    assert deactivated == 1
    refreshed = await db_session.scalar(
        select(Vacancy).where(Vacancy.id == vacancy.id).execution_options(populate_existing=True)
    )
    assert refreshed is not None and refreshed.is_active is False


@respx.mock
async def test_pipeline_end_to_end(
    db_session: AsyncSession,
    stub_database: StubDatabase,
    fake_redis: Any,
    settings: Settings,
    taxonomy_rows: None,
) -> None:
    await create_hh_source(db_session)
    user, _ = await create_profile(db_session)
    respx.get("https://api.hh.ru/vacancies").mock(
        return_value=httpx.Response(200, json=load_json("hh_page.json"))
    )

    collection = await collect_source_async(
        "hh",
        database=stub_database,
        redis=fake_redis,
        settings=settings,
        max_pages=1,
    )
    assert collection["created"] == 1

    pairs = await pending_analysis_pairs(db_session, limit=10, lookback_days=365)
    assert len(pairs) == 1
    vacancy_id, user_id = pairs[0]

    analysis = await analyze_vacancy_async(
        vacancy_id,
        user_id,
        database=stub_database,
        provider=MockAIProvider(),
        settings=settings,
    )
    assert analysis["score"] >= 50

    notifier = RecordingNotifier()
    report = await send_notifications_async(
        database=stub_database, notifier=notifier, settings=settings
    )

    assert report["sent"] == 1
    assert "Senior Python Developer" in notifier.messages[0][1]
    assert user.id == user_id
