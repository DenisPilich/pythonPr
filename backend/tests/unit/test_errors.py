from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from app.api.errors import (
    app_error_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.exceptions import AppError, NotFoundError


def build_app() -> FastAPI:
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    @app.get("/missing")
    async def missing() -> None:
        raise NotFoundError("Vacancy 42 not found")

    @app.get("/number")
    async def number(q: int) -> dict[str, int]:
        return {"q": q}

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    return app


@pytest.fixture()
def error_client() -> Iterator[TestClient]:
    with TestClient(build_app(), raise_server_exceptions=False) as client:
        yield client


def test_app_error_maps_to_problem_json(error_client: TestClient) -> None:
    response = error_client.get("/missing")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"] == "not_found"
    assert body["title"] == "Not Found"
    assert body["detail"] == "Vacancy 42 not found"
    assert body["instance"] == "/missing"
    assert body["type"].endswith("/not_found")


def test_validation_error_lists_fields(error_client: TestClient) -> None:
    response = error_client.get("/number", params={"q": "abc"})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["errors"][0]["location"] == "query.q"


def test_unhandled_error_is_masked(error_client: TestClient) -> None:
    response = error_client.get("/boom")

    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "internal_error"
    assert "boom" not in body["detail"]
