"""Telegram-ready message rendering.

Kept separate from delivery so the text can be snapshot-tested and reused by the
bot (stage 6) without touching the notification dispatcher.
"""

from __future__ import annotations

from decimal import Decimal
from html import escape

from app.domain.enums import Recommendation, SalaryPeriod


_PERIOD_LABELS = {
    SalaryPeriod.HOUR: "hour",
    SalaryPeriod.DAY: "day",
    SalaryPeriod.MONTH: "month",
    SalaryPeriod.YEAR: "year",
}


def _thousands(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def format_salary(
    *,
    minimum: int | None,
    maximum: int | None,
    currency: str | None,
    period: SalaryPeriod,
    monthly_eur: Decimal | None,
) -> str:
    if monthly_eur is not None:
        return f"~€{_thousands(int(float(monthly_eur)))} / month"
    if minimum is None and maximum is None:
        return "Not specified"
    suffix = f" / {_PERIOD_LABELS.get(period, 'period')}"
    code = f" {currency}" if currency else ""
    if minimum is not None and maximum is not None:
        return f"{_thousands(minimum)}–{_thousands(maximum)}{code}{suffix}"
    if minimum is not None:
        return f"from {_thousands(minimum)}{code}{suffix}"
    return f"up to {_thousands(maximum or 0)}{code}{suffix}"


def render_vacancy_notification(
    *,
    title: str,
    company: str,
    location: str | None,
    salary: str,
    seniority: str,
    match_score: int,
    strong_matches: list[str],
    missing_skills: list[str],
    recommendation: Recommendation,
    url: str,
) -> str:
    lines: list[str] = [
        f"🔥 <b>{escape(title)}</b> — {escape(seniority.title())}",
        "",
        f"Company: {escape(company)}",
    ]
    if location:
        lines.append(f"Location: {escape(location)}")
    lines.append(f"Salary: {escape(salary)}")
    lines += ["", f"🎯 Match: <b>{match_score}%</b>"]

    if strong_matches:
        lines += ["", "✅ Хорошее совпадение:"]
        lines += [f"- {escape(item)}" for item in strong_matches[:8]]

    if missing_skills:
        lines += ["", "❌ Не хватает:"]
        lines += [f"- {escape(item)}" for item in missing_skills[:8]]

    lines += [
        "",
        "🤖 AI recommendation:",
        f"<b>{recommendation.value.upper()}</b>",
        "",
        f'<a href="{escape(url, quote=True)}">Открыть вакансию</a>',
    ]
    return "\n".join(lines)
