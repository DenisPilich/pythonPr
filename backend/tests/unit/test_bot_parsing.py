from __future__ import annotations

from app.bot.services import parse_list, parse_salary


def test_parse_list_splits_and_deduplicates() -> None:
    assert parse_list("Python, FastAPI\nDocker; python") == [
        "Python",
        "FastAPI",
        "Docker",
    ]


def test_parse_list_drops_empty_and_overlong_items() -> None:
    long_item = "x" * 80
    assert parse_list(f"Python, , {long_item}, Go") == ["Python", "Go"]


def test_parse_list_caps_the_number_of_items() -> None:
    raw = ", ".join(f"skill{i}" for i in range(50))
    assert len(parse_list(raw)) == 30


def test_parse_salary_with_currency() -> None:
    assert parse_salary("3000 EUR") == (3000, "EUR")
    assert parse_salary("from 3 000 usd") == (3000, "USD")


def test_parse_salary_defaults_to_eur() -> None:
    assert parse_salary("2500") == (2500, "EUR")


def test_parse_salary_rejects_garbage() -> None:
    assert parse_salary("competitive") is None
    assert parse_salary("0 EUR") is None
