"""Small text helpers shared by prompts and normalizers."""

from __future__ import annotations


def truncate(text: str, limit: int) -> str:
    """Cut at a word boundary and mark the cut, for prompt budgets."""
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return f"{cut}…"
