"""Location parsing: enough structure for filters, no geocoding service."""

from __future__ import annotations

import re


_COUNTRY_NAMES: dict[str, str] = {
    "germany": "DE",
    "deutschland": "DE",
    "poland": "PL",
    "polska": "PL",
    "russia": "RU",
    "россия": "RU",
    "ukraine": "UA",
    "украина": "UA",
    "belarus": "BY",
    "беларусь": "BY",
    "kazakhstan": "KZ",
    "казахстан": "KZ",
    "romania": "RO",
    "bulgaria": "BG",
    "czech republic": "CZ",
    "czechia": "CZ",
    "slovakia": "SK",
    "hungary": "HU",
    "serbia": "RS",
    "spain": "ES",
    "portugal": "PT",
    "italy": "IT",
    "france": "FR",
    "netherlands": "NL",
    "belgium": "BE",
    "austria": "AT",
    "switzerland": "CH",
    "sweden": "SE",
    "norway": "NO",
    "denmark": "DK",
    "finland": "FI",
    "ireland": "IE",
    "united kingdom": "GB",
    "uk": "GB",
    "england": "GB",
    "united states": "US",
    "usa": "US",
    "us": "US",
    "canada": "CA",
    "mexico": "MX",
    "brazil": "BR",
    "argentina": "AR",
    "turkey": "TR",
    "israel": "IL",
    "india": "IN",
    "singapore": "SG",
    "japan": "JP",
    "australia": "AU",
    "new zealand": "NZ",
    "armenia": "AM",
    "georgia": "GE",
    "cyprus": "CY",
    "estonia": "EE",
    "latvia": "LV",
    "lithuania": "LT",
    "moldova": "MD",
    "uzbekistan": "UZ",
}
_REMOTE_MARKERS = re.compile(
    r"\b(remote|anywhere|worldwide|distributed|удал[её]нн\w*|дистанционн\w*)\b", re.I
)
_PAREN_RE = re.compile(r"\([^)]*\)")


def parse_location(raw: str | None) -> tuple[str | None, str | None]:
    """Return `(city, country_code)`; unknown parts stay None."""
    if not raw or not raw.strip():
        return None, None

    text = _PAREN_RE.sub(" ", raw).strip(" ,;-")
    if not text or _REMOTE_MARKERS.search(text):
        return None, None

    parts = [part.strip() for part in re.split(r"[,/|]", text) if part.strip()]
    if not parts:
        return None, None

    country_code = None
    for part in reversed(parts):
        code = _COUNTRY_NAMES.get(part.lower())
        if code:
            country_code = code
            break

    if country_code is None:
        code = _COUNTRY_NAMES.get(text.lower())
        if code:
            return None, code

    city = parts[0] if len(parts[0]) <= 64 else None
    if city and city.lower() in _COUNTRY_NAMES:
        city = None
    return city, country_code
