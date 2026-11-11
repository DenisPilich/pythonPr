from __future__ import annotations

from typing import Any

import httpx
import pytest


pytestmark = pytest.mark.integration

PAYLOAD: dict[str, Any] = {
    "headline": "Python backend developer",
    "desired_positions": ["Python Backend Developer"],
    "target_seniority": ["junior", "middle"],
    "skills": ["Python", "FastAPI", "PostgreSQL"],
    "preferred_stack": ["FastAPI", "PostgreSQL"],
    "english_level": "b2",
    "min_salary_amount": 2500,
    "salary_currency": "eur",
    "preferred_locations": ["Germany", "Remote"],
    "work_formats": ["remote", "hybrid"],
    "min_match_score": 75,
    "notifications_enabled": True,
    "max_notifications_per_day": 10,
}


def headers(telegram_id: int = 777) -> dict[str, str]:
    return {"X-API-Key": "test-key", "X-Telegram-Id": str(telegram_id)}


async def test_missing_profile_returns_404(api_client: httpx.AsyncClient) -> None:
    response = await api_client.get("/api/v1/profile")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


async def test_create_requires_api_key(api_client: httpx.AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/profile", json=PAYLOAD, headers={"X-Telegram-Id": "777"}
    )

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "unauthorized"


async def test_create_read_and_conflict(api_client: httpx.AsyncClient) -> None:
    created = await api_client.post("/api/v1/profile", json=PAYLOAD, headers=headers(777))

    assert created.status_code == 201
    body = created.json()
    assert body["telegram_id"] == 777
    assert body["skills"] == ["Python", "FastAPI", "PostgreSQL"]
    assert body["salary_currency"] == "EUR"
    assert len(body["profile_hash"]) == 64
    assert body["created_at"]

    duplicate = await api_client.post("/api/v1/profile", json=PAYLOAD, headers=headers(777))
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "conflict"

    fetched = await api_client.get("/api/v1/profile", headers=headers(777))
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]


async def test_put_replaces_and_recomputes_hash(api_client: httpx.AsyncClient) -> None:
    created = await api_client.post("/api/v1/profile", json=PAYLOAD, headers=headers(778))
    original_hash = created.json()["profile_hash"]

    updated = await api_client.put(
        "/api/v1/profile",
        json={**PAYLOAD, "skills": ["Python", "python", "Docker"], "min_match_score": 85},
        headers=headers(778),
    )

    assert updated.status_code == 200
    body = updated.json()
    assert body["skills"] == ["Python", "Docker"]
    assert body["min_match_score"] == 85
    assert body["profile_hash"] != original_hash


async def test_hash_is_stable_when_list_order_changes(
    api_client: httpx.AsyncClient,
) -> None:
    created = await api_client.post("/api/v1/profile", json=PAYLOAD, headers=headers(779))
    original_hash = created.json()["profile_hash"]

    reordered = await api_client.put(
        "/api/v1/profile",
        json={
            **PAYLOAD,
            "skills": ["PostgreSQL", "Python", "FastAPI"],
            "preferred_stack": ["PostgreSQL", "FastAPI"],
        },
        headers=headers(779),
    )

    assert reordered.status_code == 200
    assert reordered.json()["profile_hash"] == original_hash


async def test_put_creates_profile_when_missing(api_client: httpx.AsyncClient) -> None:
    response = await api_client.put("/api/v1/profile", json=PAYLOAD, headers=headers(780))

    assert response.status_code == 200
    assert response.json()["telegram_id"] == 780


async def test_uses_demo_user_without_header(api_client: httpx.AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/profile", json=PAYLOAD, headers={"X-API-Key": "test-key"}
    )

    assert response.status_code == 201
    assert response.json()["telegram_id"] == 100_000_001


@pytest.mark.parametrize(
    "override",
    [
        {"min_match_score": 150},
        {"salary_currency": "EURO"},
        {"target_seniority": ["wizard"]},
        {"max_notifications_per_day": -1},
    ],
)
async def test_validation_errors(api_client: httpx.AsyncClient, override: dict[str, Any]) -> None:
    response = await api_client.put(
        "/api/v1/profile", json={**PAYLOAD, **override}, headers=headers(781)
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
