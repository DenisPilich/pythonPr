from __future__ import annotations

from typing import Any

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import UserVacancyStatus
from app.models import UserVacancy
from tests.integration.test_analysis_service import create_profile
from tests.integration.test_api_jobs import dataset  # noqa: F401  # shared fixture


pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("taxonomy_rows")]


@pytest.fixture()
def jobs(request: pytest.FixtureRequest) -> dict[str, Any]:
    return request.getfixturevalue("dataset")


async def test_history_returns_items_and_counts(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    jobs: dict[str, Any],
) -> None:
    user, _ = await create_profile(db_session, telegram_id=9001)
    db_session.add_all(
        [
            UserVacancy(
                user_id=user.id,
                vacancy_id=jobs["senior"].id,
                status=UserVacancyStatus.SAVED,
                match_score=90,
            ),
            UserVacancy(
                user_id=user.id,
                vacancy_id=jobs["junior"].id,
                status=UserVacancyStatus.APPLIED,
                match_score=60,
            ),
        ]
    )
    await db_session.flush()

    response = await api_client.get("/api/v1/history", headers={"X-Telegram-Id": "9001"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["counts"]["saved"] == 1
    assert body["counts"]["applied"] == 1
    assert body["counts"]["total"] == 2
    statuses = {item["status"] for item in body["items"]}
    assert statuses == {"saved", "applied"}


async def test_history_filters_by_status(
    api_client: httpx.AsyncClient,
    db_session: AsyncSession,
    jobs: dict[str, Any],
) -> None:
    user, _ = await create_profile(db_session, telegram_id=9002)
    db_session.add_all(
        [
            UserVacancy(
                user_id=user.id,
                vacancy_id=jobs["senior"].id,
                status=UserVacancyStatus.SAVED,
                match_score=90,
            ),
            UserVacancy(
                user_id=user.id,
                vacancy_id=jobs["data"].id,
                status=UserVacancyStatus.REJECTED,
                match_score=30,
            ),
        ]
    )
    await db_session.flush()

    response = await api_client.get(
        "/api/v1/history",
        params={"status": "saved"},
        headers={"X-Telegram-Id": "9002"},
    )

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["status"] == "saved"


async def test_history_for_unknown_user_is_empty(
    api_client: httpx.AsyncClient, jobs: dict[str, Any]
) -> None:
    response = await api_client.get("/api/v1/history", headers={"X-Telegram-Id": "999999"})

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["counts"]["total"] == 0
