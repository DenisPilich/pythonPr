"""Salary parsing and cross-currency normalization.

Job boards express pay in every possible way: `"€1.2k–1.8k / month"`,
`"120 000 – 180 000 ₽"`, `"$60k - $80k per year"`, `"from 2000 EUR"`.
The parser returns a `SalaryInput` and a normalized monthly EUR figure used for
filtering; it never guesses a currency out of thin air.

Period inference is intentionally conservative. When a period is missing we use
magnitude heuristics that hold for the covered markets (monthly RUB/KZT/UAH,
monthly small EUR/USD, annual large EUR/USD) and leave `UNKNOWN` in the ambiguous
15k–30k band rather than inventing a value that would poison filters.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from app.domain.dto import NormalizedSalary, SalaryInput
from app.domain.enums import SalaryPeriod
from app.domain.money import FX_TO_EUR


_CURRENCY_SYMBOLS = {
    "€": "EUR",
    "$": "USD",
    "£": "GBP",
    "₽": "RUB",
    "₸": "KZT",
    "₴": "UAH",
    "zł": "PLN",
    "Kč": "CZK",
    "₪": "ILS",
    "₹": "INR",
}

_PERIOD_PATTERNS: tuple[tuple[SalaryPeriod, re.Pattern[str]], ...] = (
    (
        SalaryPeriod.HOUR,
        re.compile(r"(per\s+hour|/\s*hour|hourly|в\s+час|за\s+час|час\b)", re.I),
    ),
    (SalaryPeriod.DAY, re.compile(r"(per\s+day|/\s*day|daily|в\s+день|за\s+день)", re.I)),
    (
        SalaryPeriod.MONTH,
        re.compile(r"(per\s+month|/\s*month|monthly|в\s+месяц|за\s+месяц|в\s+мес\b)", re.I),
    ),
    (
        SalaryPeriod.YEAR,
        re.compile(r"(per\s+year|/\s*year|per\s+annum|annually|annual|в\s+год|за\s+год)", re.I),
    ),
)

_MONTH_FACTOR = {
    SalaryPeriod.HOUR: Decimal("160"),
    SalaryPeriod.DAY: Decimal("21"),
    SalaryPeriod.MONTH: Decimal("1"),
    SalaryPeriod.YEAR: Decimal("1") / Decimal("12"),
}

_NUMBER_RE = re.compile(
    r"(?<!\d)(?P<number>\d{1,3}(?:[ \u202f,]\d{3})+|\d+(?:[.,]\d+)?)(?P<scale>\s*[kк](?!\w))?",
    re.IGNORECASE,
)
_UPPER_BOUND_RE = re.compile(r"\b(up to|max|maximum|до|не более|not more than)\b", re.I)
_LOWER_BOUND_RE = re.compile(r"\b(from|starting at|min|minimum|от|начиная с)\b", re.I)

# Below/above these a "monthly EUR" figure is almost certainly source noise
# (RemoteOK occasionally ships six-figure hourly rates typed into annual fields).
_MIN_PLAUSIBLE_MONTHLY_EUR = Decimal("100")
_MAX_PLAUSIBLE_MONTHLY_EUR = Decimal("100000")


def _detect_currency(text: str, default_currency: str | None) -> str | None:
    for symbol, code in _CURRENCY_SYMBOLS.items():
        if symbol in text:
            return code
    for token in re.findall(r"\b[a-zA-Z]{3}\b", text):
        candidate = str(token).upper()
        if candidate in FX_TO_EUR:
            return candidate
    if default_currency:
        return default_currency.upper()
    return None


def _detect_period(text: str) -> SalaryPeriod:
    for period, pattern in _PERIOD_PATTERNS:
        if pattern.search(text):
            return period
    return SalaryPeriod.UNKNOWN


def _to_int(raw: str, scale: str | None) -> int | None:
    value = raw.replace("\u202f", "").replace(" ", "")
    try:
        if scale:
            decimal = Decimal(value.replace(",", "."))
            return int(decimal * 1000)
        if re.fullmatch(r"\d{1,3}([.,]\d{3})+", value):
            return int(re.sub(r"[.,]", "", value))
        if re.fullmatch(r"\d+[.,]\d+", value):
            return int(Decimal(value.replace(",", ".")))
        return int(value)
    except (InvalidOperation, ValueError):
        return None


def _infer_period(amount: int, currency: str | None, stated: SalaryPeriod) -> SalaryPeriod:
    if stated is not SalaryPeriod.UNKNOWN or amount <= 0:
        return stated
    code = (currency or "").upper()
    if code in {"RUB", "KZT", "UAH"}:
        return SalaryPeriod.MONTH if amount >= 30_000 else SalaryPeriod.UNKNOWN
    if code in {"EUR", "USD", "GBP", "CHF"}:
        if amount >= 30_000:
            return SalaryPeriod.YEAR
        if amount <= 15_000:
            return SalaryPeriod.MONTH
    return SalaryPeriod.UNKNOWN


def parse_salary_text(
    text: str | None, *, default_currency: str | None = None
) -> SalaryInput | None:
    """Parse a free-form salary string; returns None when no number is present."""
    if not text:
        return None
    cleaned = text.replace("\xa0", " ").strip()
    matches = list(_NUMBER_RE.finditer(cleaned))
    amounts = [
        amount
        for match in matches
        if (amount := _to_int(match.group("number"), match.group("scale"))) is not None
    ]
    if not amounts:
        return None

    currency = _detect_currency(cleaned, default_currency)
    period = _detect_period(cleaned)

    if len(amounts) >= 2:
        low, high = sorted(amounts[:2])
        return SalaryInput(min=low, max=high, currency=currency, period=period, is_estimated=False)

    value = amounts[0]
    if _UPPER_BOUND_RE.search(cleaned):
        return SalaryInput(min=None, max=value, currency=currency, period=period, is_estimated=True)
    if _LOWER_BOUND_RE.search(cleaned):
        return SalaryInput(min=value, max=None, currency=currency, period=period, is_estimated=True)
    return SalaryInput(min=value, max=value, currency=currency, period=period, is_estimated=False)


def monthly_eur(amount: int | None, currency: str | None, period: SalaryPeriod) -> Decimal | None:
    if not amount or amount <= 0 or not currency or period is SalaryPeriod.UNKNOWN:
        return None
    rate = FX_TO_EUR.get(currency.upper())
    if rate is None:
        return None
    monthly = (Decimal(amount) * _MONTH_FACTOR[period] * rate).quantize(Decimal("0.01"))
    if not (_MIN_PLAUSIBLE_MONTHLY_EUR <= monthly <= _MAX_PLAUSIBLE_MONTHLY_EUR):
        return None
    return monthly


def normalize_salary(value: SalaryInput | None) -> NormalizedSalary | None:
    """Attach an inferred period and a monthly EUR equivalent."""
    if value is None:
        return None
    low, high = value.min, value.max
    if low is not None and high is not None and low > high:
        low, high = high, low
    if low is None and high is None:
        return None
    currency = value.currency.upper() if value.currency else None

    reference = high if high is not None else low
    period = _infer_period(reference or 0, currency, value.period)
    midpoint = int((low + high) / 2) if low is not None and high is not None else reference

    return NormalizedSalary(
        min=low,
        max=high,
        currency=currency,
        period=period,
        is_estimated=value.is_estimated,
        monthly_eur=monthly_eur(midpoint, currency, period),
    )
