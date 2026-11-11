from __future__ import annotations

from fastapi.testclient import TestClient


def test_liveness_is_ok(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"]


def test_meta_exposes_service_identity(client: TestClient) -> None:
    response = client.get("/api/v1/meta")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "AI Job Radar"
    assert body["api_prefix"] == "/api/v1"
    assert body["docs_url"] == "/docs"


def test_root_points_to_docs(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["docs"] == "/docs"


def test_request_id_is_echoed(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "abc-123"})
    assert response.headers["x-request-id"] == "abc-123"


def test_request_id_is_generated_when_missing(client: TestClient) -> None:
    response = client.get("/health/live")
    assert len(response.headers["x-request-id"]) == 32


def test_openapi_schema_is_served(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "/health/live" in schema["paths"]
    assert "/api/v1/meta" in schema["paths"]
