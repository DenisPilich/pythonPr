from __future__ import annotations

from decimal import Decimal

from app.domain.enums import Recommendation, SalaryPeriod
from app.services.notification_format import format_salary, render_vacancy_notification


def test_salary_prefers_normalized_monthly_eur() -> None:
    assert (
        format_salary(
            minimum=60000,
            maximum=80000,
            currency="EUR",
            period=SalaryPeriod.YEAR,
            monthly_eur=Decimal("5366.67"),
        )
        == "~€5 366 / month"
    )


def test_salary_range_with_currency_and_period() -> None:
    assert (
        format_salary(
            minimum=1200,
            maximum=1800,
            currency="EUR",
            period=SalaryPeriod.MONTH,
            monthly_eur=None,
        )
        == "1 200–1 800 EUR / month"
    )


def test_salary_lower_and_upper_bounds() -> None:
    assert (
        format_salary(
            minimum=2000,
            maximum=None,
            currency="USD",
            period=SalaryPeriod.MONTH,
            monthly_eur=None,
        )
        == "from 2 000 USD / month"
    )
    assert (
        format_salary(
            minimum=None,
            maximum=3000,
            currency="EUR",
            period=SalaryPeriod.MONTH,
            monthly_eur=None,
        )
        == "up to 3 000 EUR / month"
    )


def test_salary_unknown() -> None:
    assert (
        format_salary(
            minimum=None,
            maximum=None,
            currency=None,
            period=SalaryPeriod.UNKNOWN,
            monthly_eur=None,
        )
        == "Not specified"
    )


def test_render_contains_match_and_actions() -> None:
    text = render_vacancy_notification(
        title="Senior Python Developer",
        company="Acme & Co",
        location="Remote",
        salary="~€5 000 / month",
        seniority="senior",
        match_score=87,
        strong_matches=["Python", "FastAPI"],
        missing_skills=["Docker"],
        recommendation=Recommendation.APPLY,
        url="https://example.com/jobs/1",
    )

    assert "🔥 <b>Senior Python Developer</b> — Senior" in text
    assert "Acme &amp; Co" in text
    assert "🎯 Match: <b>87%</b>" in text
    assert "✅ Хорошее совпадение:" in text
    assert "- Python" in text
    assert "❌ Не хватает:" in text
    assert "<b>APPLY</b>" in text
    assert '<a href="https://example.com/jobs/1">Открыть вакансию</a>' in text


def test_render_escapes_user_controlled_html() -> None:
    text = render_vacancy_notification(
        title="<script>alert(1)</script>",
        company="A & B",
        location=None,
        salary="Not specified",
        seniority="middle",
        match_score=50,
        strong_matches=[],
        missing_skills=[],
        recommendation=Recommendation.CONSIDER,
        url="https://example.com/?a=1&b=2",
    )

    assert "<script>" not in text
    assert "&lt;script&gt;" in text
    assert "A &amp; B" in text
    assert "a=1&amp;b=2" in text


def test_render_omits_empty_sections() -> None:
    text = render_vacancy_notification(
        title="Developer",
        company="Acme",
        location="Berlin",
        salary="Not specified",
        seniority="middle",
        match_score=55,
        strong_matches=[],
        missing_skills=[],
        recommendation=Recommendation.CONSIDER,
        url="https://example.com",
    )

    assert "✅" not in text
    assert "❌" not in text
