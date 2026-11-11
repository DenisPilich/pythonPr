from __future__ import annotations

from typing import Any

import httpx
import pytest

from tests.integration.test_api_jobs import dataset  # noqa: F401  # shared fixture


pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("taxonomy_rows"),
]

PROFILE: dict[str, Any] = {
    "headline": "Python backend developer",
    "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
    "preferred_stack": ["FastAPI"],
    "target_seniority": ["senior"],
    "work_formats": ["remote"],
    "min_salary_amount": 3000,
    "salary_currency": "EUR",
    "min_match_score": 70,
}


@pytest.fixture()
def jobs(dataset: dict[str, Any]) -> dict[str, Any]:  # noqa: F811
    return dataset


def headers(telegram_id: int = 777) -> dict[str, str]:
    return {"X-API-Key": "test-key", "X-Telegram-Id": str(telegram_id)}


async def create_profile(api_client: httpx.AsyncClient, telegram_id: int = 777) -> None:
    response = await api_client.put("/api/v1/profile", json=PROFILE, headers=headers(telegram_id))
    assert response.status_code == 200


async def test_analyze_then_read_analysis(
    api_client: httpx.AsyncClient, jobs: dict[str, Any]
) -> None:
    await create_profile(api_client)
    job_id = jobs["senior"].id

    first = await api_client.post(f"/api/v1/jobs/{job_id}/analyze", headers=headers())
    assert first.status_code == 200
    body = first.json()
    assert body["provider"] == "mock"
    assert body["match_score"] >= 75
    assert body["recommendation"] == "apply"
    assert first.headers["x-analysis-cached"] == "false"
    assert first.headers["x-analysis-skipped"] == "false"

    second = await api_client.post(f"/api/v1/jobs/{job_id}/analyze", headers=headers())
    assert second.status_code == 200
    assert second.headers["x-analysis-cached"] == "true"
    assert second.json()["id"] == body["id"]

    fetched = await api_client.get(
        f"/api/v1/jobs/{job_id}/analysis", headers={"X-Telegram-Id": "777"}
    )
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]


async def test_analyze_requires_api_key(
    api_client: httpx.AsyncClient, jobs: dict[str, Any]
) -> None:
    job_id = jobs["senior"].id
    response = await api_client.post(
        f"/api/v1/jobs/{job_id}/analyze", headers={"X-Telegram-Id": "777"}
    )

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


async def test_analyze_requires_profile(
    api_client: httpx.AsyncClient, jobs: dict[str, Any]
) -> None:
    response = await api_client.post(
        f"/api/v1/jobs/{jobs['senior'].id}/analyze", headers=headers(999)
    )

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


async def test_analysis_not_found_before_first_run(
    api_client: httpx.AsyncClient, jobs: dict[str, Any]
) -> None:
    await create_profile(api_client)
    response = await api_client.get(
        f"/api/v1/jobs/{jobs['junior'].id}/analysis",
        headers={"X-Telegram-Id": "777"},
    )

    assert response.status_code == 404


async def test_prefilter_is_reported(api_client: httpx.AsyncClient, jobs: dict[str, Any]) -> None:
    await api_client.put(
        "/api/v1/profile",
        json={**PROFILE, "target_seniority": ["junior"]},
        headers=headers(778),
    )

    response = await api_client.post(
        f"/api/v1/jobs/{jobs['senior'].id}/analyze", headers=headers(778)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "prefilter"
    assert body["match_score"] == 0
    assert body["recommendation"] == "skip"
    assert response.headers["x-analysis-skipped"] == "true"
