"""Company name canonicalization.

`"Acme, Inc."`, `"ACME LLC"` and `"Acme"` must collapse to one `companies` row,
otherwise the company filter in the dashboard fragments and the same employer
creates three rows per week.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


_LEGAL_SUFFIXES = {
    "inc",
    "incorporated",
    "llc",
    "ltd",
    "limited",
    "gmbh",
    "mbh",
    "ag",
    "sa",
    "sas",
    "sarl",
    "bv",
    "nv",
    "oy",
    "oyj",
    "ab",
    "as",
    "plc",
    "corp",
    "corporation",
    "co",
    "company",
    "group",
    "holding",
    "holdings",
    "international",
    "global",
    "ventures",
    "labs",
    "studio",
    "studios",
    "llp",
    "pte",
    "sro",
    "spa",
}
_PUNCT_RE = re.compile(r"[^\w\s&]+", re.UNICODE)
_SPACE_RE = re.compile(r"\s+", re.UNICODE)


@dataclass(frozen=True, slots=True)
class CompanyIdentity:
    display: str
    key: str


def normalize_company(raw: str) -> CompanyIdentity:
    """Return a display form and a comparison key."""
    display = _SPACE_RE.sub(" ", (raw or "").strip()).strip(" ,;-–—|")
    if not display:
        return CompanyIdentity(display="Unknown", key="unknown")

    lowered = display.lower().replace("&", " and ")
    lowered = _PUNCT_RE.sub(" ", lowered)
    tokens = [token for token in lowered.split() if token]
    while len(tokens) > 1 and tokens[-1] in _LEGAL_SUFFIXES:
        tokens.pop()

    key = " ".join(tokens).strip()
    return CompanyIdentity(display=display, key=key or display.lower())
