"""Application error hierarchy.

Services raise these; the API layer maps them to RFC 7807 problem responses and
the bot layer maps them to user-friendly Telegram messages. No HTTP concepts
leak into the service layer.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for expected, mapped failures."""

    status_code: int = 500
    code: str = "internal_error"
    title: str = "Internal Server Error"

    def __init__(
        self,
        detail: str | None = None,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.detail = detail or self.title
        self.details: dict[str, Any] = details or {}
        if code is not None:
            self.code = code
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    title = "Not Found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    title = "Conflict"


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"
    title = "Unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"
    title = "Forbidden"


class InvalidInputError(AppError):
    status_code = 422
    code = "invalid_input"
    title = "Invalid Input"


class RateLimitedError(AppError):
    status_code = 429
    code = "rate_limited"
    title = "Too Many Requests"


class ExternalServiceError(AppError):
    """A third-party dependency failed in a way the caller cannot fix."""

    status_code = 502
    code = "external_service_error"
    title = "Bad Gateway"


class AIProviderError(ExternalServiceError):
    code = "ai_provider_error"


class BudgetExceededError(AppError):
    status_code = 429
    code = "ai_budget_exceeded"
    title = "AI Budget Exceeded"


class ConfigurationError(AppError):
    status_code = 500
    code = "configuration_error"
    title = "Configuration Error"
