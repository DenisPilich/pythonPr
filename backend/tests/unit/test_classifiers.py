from __future__ import annotations

import pytest

from app.domain.enums import SeniorityLevel, VacancyLanguage, WorkFormat
from app.normalization.language import detect_language
from app.normalization.location import parse_location
from app.normalization.seniority import detect_seniority
from app.normalization.work_format import detect_work_format


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Senior Python Developer", SeniorityLevel.SENIOR),
        ("Junior Backend Engineer", SeniorityLevel.JUNIOR),
        ("Middle Python Developer", SeniorityLevel.MIDDLE),
        ("Team Lead", SeniorityLevel.LEAD),
        ("Software Engineer Intern", SeniorityLevel.INTERN),
        ("Python Developer", SeniorityLevel.UNKNOWN),
        ("Sr. Backend Developer", SeniorityLevel.SENIOR),
    ],
)
def test_seniority_from_title(title: str, expected: SeniorityLevel) -> None:
    assert detect_seniority(title) is expected


def test_seniority_falls_back_to_description_years() -> None:
    assert detect_seniority("Python Developer", "You have 5+ years of experience") is (
        SeniorityLevel.SENIOR
    )
    assert detect_seniority("Python Developer", "2 years of experience required") is (
        SeniorityLevel.MIDDLE
    )


def test_seniority_title_wins_over_description() -> None:
    assert detect_seniority("Junior Developer", "5+ years of experience") is (SeniorityLevel.JUNIOR)


@pytest.mark.parametrize(
    ("location", "description", "expected"),
    [
        ("Remote", "", WorkFormat.REMOTE),
        ("Berlin, Germany", "Hybrid role, 2 days in office", WorkFormat.HYBRID),
        ("London", "On-site only", WorkFormat.OFFICE),
        ("", "Fully remote team", WorkFormat.REMOTE),
        ("", "Relocation required", WorkFormat.OFFICE),
        ("Berlin", "Great team", WorkFormat.UNKNOWN),
        ("", "Удалённая работа", WorkFormat.REMOTE),
        ("", "Гибридный формат", WorkFormat.HYBRID),
    ],
)
def test_work_format(location: str, description: str, expected: WorkFormat) -> None:
    assert detect_work_format(location, description) is expected


def test_explicit_hint_wins() -> None:
    assert detect_work_format("Remote", "on-site", WorkFormat.HYBRID) is WorkFormat.HYBRID


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("We are looking for a Python developer to join our team", VacancyLanguage.EN),
        ("Требуется Python разработчик в команду", VacancyLanguage.RU),
        ("Шукаємо розробника Python", VacancyLanguage.UK),
        ("Wir suchen einen Entwickler mit Python und Docker", VacancyLanguage.DE),
        ("Szukamy programisty Python do zespołu", VacancyLanguage.PL),
        ("", VacancyLanguage.UNKNOWN),
        ("12345 !!!", VacancyLanguage.UNKNOWN),
    ],
)
def test_language(text: str, expected: VacancyLanguage) -> None:
    assert detect_language(text) is expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Berlin, Germany", ("Berlin", "DE")),
        ("Moscow, Russia", ("Moscow", "RU")),
        ("Poland", (None, "PL")),
        ("Kyiv, Ukraine", ("Kyiv", "UA")),
        ("Remote", (None, None)),
        ("Remote (Europe)", (None, None)),
        (None, (None, None)),
    ],
)
def test_parse_location(raw: str | None, expected: tuple[str | None, str | None]) -> None:
    assert parse_location(raw) == expected
