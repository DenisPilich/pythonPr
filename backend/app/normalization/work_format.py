"""Work-format detection.

Priority: explicit source hint → hybrid markers → remote markers → office
markers. Hybrid is checked before remote because "hybrid remote" is a hybrid
role, and remote-before-office because "remote-friendly office" is remote.
"""

from __future__ import annotations

import re

from app.domain.enums import WorkFormat


_HYBRID_RE = re.compile(
    r"\b(hybrid|гибрид\w*|partially remote|partly remote|partially distributed|"
    r"\d+\s*days?\s*(?:a|per)\s*week\s+in\s+(?:the\s+)?office)\b",
    re.I,
)
_REMOTE_RE = re.compile(
    r"\b(remote|remotely|fully remote|remote[- ]first|work from home|wfh|"
    r"anywhere|distributed team|удал[её]нн\w*|дистанционн\w*)\b",
    re.I,
)
_OFFICE_RE = re.compile(
    r"\b(on[- ]?site|in[- ]office|office[- ]based|office only|relocation required|"
    r"офис\w*|в офисе|релокац\w*)\b",
    re.I,
)


def detect_work_format(
    location: str | None,
    description: str = "",
    hint: WorkFormat | None = None,
) -> WorkFormat:
    if hint is not None and hint is not WorkFormat.UNKNOWN:
        return hint

    haystack = f"{location or ''}\n{description[:3000]}"
    if _HYBRID_RE.search(haystack):
        return WorkFormat.HYBRID
    if _REMOTE_RE.search(haystack):
        return WorkFormat.REMOTE
    if _OFFICE_RE.search(haystack):
        return WorkFormat.OFFICE
    return WorkFormat.UNKNOWN
