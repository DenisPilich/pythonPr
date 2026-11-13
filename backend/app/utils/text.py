"""Small text helpers shared by prompts and normalizers."""

from __future__ import annotations


_MOJIBAKE_MARKERS = ("â€", "â", "Ã", "Â", "ðŸ")


def truncate(text: str, limit: int) -> str:
    """Cut at a word boundary and mark the cut, for prompt budgets."""
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return f"{cut}…"


def repair_mojibake(text: str) -> str:
    """Undo the common UTF-8-decoded-as-cp1252 corruption in source feeds.

    RemoteOK occasionally double-encodes titles (`â€”` instead of `—`). The
    round-trip is only attempted when a telltale marker is present, so normal
    English/Cyrillic text is never re-encoded.
    """
    if not text or not any(marker in text for marker in _MOJIBAKE_MARKERS):
        return text

    for encoding in ("cp1252", "latin-1"):
        try:
            candidate = text.encode(encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if candidate.count("\ufffd") <= text.count("\ufffd"):
            return candidate
    return text
