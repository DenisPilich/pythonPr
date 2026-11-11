"""Model registry — importing this package registers every table on `Base.metadata`."""

from app.models.entities import (
    AIAnalysis,
    CollectorRun,
    Company,
    Notification,
    Source,
    Technology,
    User,
    UserProfile,
    UserVacancy,
    Vacancy,
    VacancySource,
    VacancyTechnology,
)

__all__ = [
    "AIAnalysis",
    "CollectorRun",
    "Company",
    "Notification",
    "Source",
    "Technology",
    "User",
    "UserProfile",
    "UserVacancy",
    "Vacancy",
    "VacancySource",
    "VacancyTechnology",
]
