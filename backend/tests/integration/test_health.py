from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


pytestmark = pytest.mark.integration


def test_readiness_reports_healthy_dependencies(integration_client: TestClient) -> None:
    if not os.getenv("TEST_REDIS_URL"):
        pytest.skip("TEST_REDIS_URL is not set")

    response = integration_client.get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"] == {"database": "ok", "redis": "ok"}


def test_meta_works_against_real_database(integration_client: TestClient) -> None:
    response = integration_client.get("/api/v1/meta")
    assert response.status_code == 200
