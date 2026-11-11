"""Domain enumerations shared by ORM models, Pydantic schemas and business rules.

All values are lowercase strings so they can be stored in native PostgreSQL
enums, serialized to JSON and rendered in the UI without translation tables.
"""

from __future__ import annotations

from enum import StrEnum


class WorkFormat(StrEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    OFFICE = "office"
    UNKNOWN = "unknown"


class SeniorityLevel(StrEnum):
    INTERN = "intern"
    JUNIOR = "junior"
    MIDDLE = "middle"
    SENIOR = "senior"
    LEAD = "lead"
    UNKNOWN = "unknown"


class SalaryPeriod(StrEnum):
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"
    YEAR = "year"
    UNKNOWN = "unknown"


class VacancyLanguage(StrEnum):
    EN = "en"
    RU = "ru"
    UK = "uk"
    DE = "de"
    PL = "pl"
    ES = "es"
    OTHER = "other"
    UNKNOWN = "unknown"


class EnglishLevel(StrEnum):
    A1 = "a1"
    A2 = "a2"
    B1 = "b1"
    B2 = "b2"
    C1 = "c1"
    C2 = "c2"
    NATIVE = "native"
    UNKNOWN = "unknown"


class TechnologyCategory(StrEnum):
    LANGUAGE = "language"
    FRAMEWORK = "framework"
    DATABASE = "database"
    DEVOPS = "devops"
    CLOUD = "cloud"
    FRONTEND = "frontend"
    MOBILE = "mobile"
    TESTING = "testing"
    MESSAGING = "messaging"
    OTHER = "other"


class SourceKind(StrEnum):
    JSON_API = "json_api"
    RSS = "rss"
    HTML = "html"


class CollectorRunStatus(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class Recommendation(StrEnum):
    APPLY = "apply"
    CONSIDER = "consider"
    SKIP = "skip"


class UserVacancyStatus(StrEnum):
    NEW = "new"
    VIEWED = "viewed"
    SAVED = "saved"
    APPLIED = "applied"
    REJECTED = "rejected"


class NotificationChannel(StrEnum):
    TELEGRAM = "telegram"


class NotificationStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


def enum_values(enum_cls: type[StrEnum]) -> list[str]:
    """Values in declaration order — used for PostgreSQL enum DDL and docs."""
    return [member.value for member in enum_cls]
