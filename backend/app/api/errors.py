"""RFC 7807 problem responses and exception handlers.

One error shape for the whole API: the dashboard, the bot and curl users all get
`type`, `title`, `status`, `detail`, `code`, `instance` and a request id.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError


logger = structlog.get_logger(__name__)

PROBLEM_CONTENT_TYPE = "application/problem+json"


def problem_response(
    request: Request,
    *,
    status: int,
    code: str,
    title: str,
    detail: str,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": f"https://errors.ai-job-radar.dev/{code}",
        "title": title,
        "status": status,
        "detail": detail,
        "code": code,
        "instance": request.url.path,
    }
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        body["request_id"] = request_id
    if errors:
        body["errors"] = errors
    return JSONResponse(status_code=status, content=body, media_type=PROBLEM_CONTENT_TYPE)


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, AppError):  # defensive: handler is registered for AppError
        return await unhandled_exception_handler(request, exc)
    return problem_response(
        request,
        status=exc.status_code,
        code=exc.code,
        title=exc.title,
        detail=exc.detail,
        errors=None,
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        return await unhandled_exception_handler(request, exc)

    errors = [
        {
            "location": ".".join(str(part) for part in error.get("loc", ())),
            "message": error.get("msg", "invalid value"),
            "type": error.get("type", "value_error"),
        }
        for error in exc.errors()
    ]
    return problem_response(
        request,
        status=422,
        code="validation_error",
        title="Request Validation Error",
        detail="One or more request parameters are invalid.",
        errors=errors,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "unhandled_exception",
        error_type=type(exc).__name__,
        path=request.url.path,
    )
    return problem_response(
        request,
        status=500,
        code="internal_error",
        title="Internal Server Error",
        detail="An unexpected error occurred. Quote the request id when reporting it.",
    )
