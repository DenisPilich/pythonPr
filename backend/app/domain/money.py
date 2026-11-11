"""Static currency conversion used by salary filters and heuristic scoring."""

from __future__ import annotations

from decimal import Decimal


# Approximate EUR per unit, refreshed manually. A live FX feed is in the backlog;
# matching must not depend on a third-party service being available.
FX_TO_EUR: dict[str, Decimal] = {
    "EUR": Decimal("1"),
    "USD": Decimal("0.92"),
    "GBP": Decimal("1.17"),
    "CHF": Decimal("1.06"),
    "RUB": Decimal("0.010"),
    "PLN": Decimal("0.23"),
    "UAH": Decimal("0.022"),
    "KZT": Decimal("0.0019"),
    "CZK": Decimal("0.040"),
    "RON": Decimal("0.20"),
    "BGN": Decimal("0.51"),
    "HUF": Decimal("0.0026"),
    "SEK": Decimal("0.088"),
    "NOK": Decimal("0.086"),
    "DKK": Decimal("0.134"),
    "TRY": Decimal("0.027"),
    "CAD": Decimal("0.68"),
    "AUD": Decimal("0.61"),
    "INR": Decimal("0.011"),
    "SGD": Decimal("0.69"),
    "AED": Decimal("0.25"),
    "ILS": Decimal("0.25"),
    "JPY": Decimal("0.0061"),
    "CNY": Decimal("0.13"),
}


def to_eur(amount: int | Decimal | None, currency: str | None) -> Decimal | None:
    if amount is None or not currency:
        return None
    rate = FX_TO_EUR.get(currency.upper())
    if rate is None:
        return None
    return (Decimal(amount) * rate).quantize(Decimal("0.01"))
