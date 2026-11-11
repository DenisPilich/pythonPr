"""Deduplication keys.

Fingerprint = company + title + location — the stable identity of a posting across
boards. Salary is deliberately excluded: one source often omits it, and including
it would split one job into two. `content_hash` covers the cleaned description and
answers a different question: "did this vacancy actually change?".
"""

from __future__ import annotations

import hashlib
import re

from app.domain.enums import WorkFormat


_PUNCT_RE = re.compile(r"[^\w\s+#.]", re.UNICODE)
_SPACE_RE = re.compile(r"\s+", re.UNICODE)

FINGERPRINT_VERSION = 1


def normalize_title(title: str) -> str:
    lowered = _PUNCT_RE.sub(" ", (title or "").lower())
    return _SPACE_RE.sub(" ", lowered).strip()


def location_key(*, city: str | None, country_code: str | None, work_format: WorkFormat) -> str:
    if work_format is WorkFormat.REMOTE:
        return "remote"
    if city:
        return _SPACE_RE.sub(" ", city.lower()).strip()
    if country_code:
        return country_code.lower()
    return "unknown"


def build_fingerprint(company_key: str, title: str, *, location: str) -> str:
    payload = f"{company_key.strip().lower()}|{normalize_title(title)}|{location}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
