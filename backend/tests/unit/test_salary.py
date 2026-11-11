from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.dto import SalaryInput
from app.domain.enums import SalaryPeriod
from app.normalization.salary import normalize_salary, parse_salary_text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "€1200–1800 / month",
            SalaryInput(1200, 1800, "EUR", SalaryPeriod.MONTH, False),
        ),
        (
            "$60k - $80k per year",
            SalaryInput(60000, 80000, "USD", SalaryPeriod.YEAR, False),
        ),
        (
            "120 000 – 180 000 ₽",
            SalaryInput(120000, 180000, "RUB", SalaryPeriod.UNKNOWN, False),
        ),
        ("from $2,000", SalaryInput(2000, None, "USD", SalaryPeriod.UNKNOWN, True)),
        ("up to 3000 EUR", SalaryInput(None, 3000, "EUR", SalaryPeriod.UNKNOWN, True)),
        ("£500/day", SalaryInput(500, 500, "GBP", SalaryPeriod.DAY, False)),
        (
            "1.2k–1.8k EUR monthly",
            SalaryInput(1200, 1800, "EUR", SalaryPeriod.MONTH, False),
        ),
        ("150000 KZT", SalaryInput(150000, 150000, "KZT", SalaryPeriod.UNKNOWN, False)),
    ],
)
def test_parse_salary_text(text: str, expected: SalaryInput) -> None:
    assert parse_salary_text(text) == expected


@pytest.mark.parametrize("text", ["Competitive salary", "", None, "Negotiable"])
def test_parse_salary_without_numbers(text: str | None) -> None:
    assert parse_salary_text(text) is None


def test_normalize_salary_adds_monthly_eur() -> None:
    normalized = normalize_salary(SalaryInput(1200, 1800, "EUR", SalaryPeriod.MONTH))
    assert normalized is not None
    assert normalized.monthly_eur == Decimal("1500.00")


def test_normalize_salary_infers_month_for_rub() -> None:
    normalized = normalize_salary(SalaryInput(120000, 180000, "RUB"))
    assert normalized is not None
    assert normalized.period is SalaryPeriod.MONTH
    assert normalized.monthly_eur is not None


def test_normalize_salary_infers_year_for_large_usd() -> None:
    normalized = normalize_salary(SalaryInput(120000, 160000, "USD"))
    assert normalized is not None
    assert normalized.period is SalaryPeriod.YEAR


def test_normalize_salary_keeps_unknown_for_ambiguous_amount() -> None:
    normalized = normalize_salary(SalaryInput(20000, 25000, "EUR"))
    assert normalized is not None
    assert normalized.period is SalaryPeriod.UNKNOWN
    assert normalized.monthly_eur is None


def test_normalize_salary_unknown_currency_has_no_monthly_value() -> None:
    normalized = normalize_salary(SalaryInput(1000, 2000, "XYZ", SalaryPeriod.MONTH))
    assert normalized is not None
    assert normalized.monthly_eur is None


def test_normalize_salary_swaps_reversed_bounds() -> None:
    normalized = normalize_salary(SalaryInput(5000, 3000, "EUR", SalaryPeriod.MONTH))
    assert normalized is not None
    assert (normalized.min, normalized.max) == (3000, 5000)


def test_normalize_salary_none() -> None:
    assert normalize_salary(None) is None


def test_implausible_salary_keeps_raw_but_drops_monthly_eur() -> None:
    normalized = normalize_salary(SalaryInput(114_000_000, 140_000_000, "USD", SalaryPeriod.YEAR))
    assert normalized is not None
    assert normalized.min == 114_000_000
    assert normalized.monthly_eur is None
