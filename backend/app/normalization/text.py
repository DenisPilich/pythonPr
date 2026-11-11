"""HTML → plain text.

A hand-written `HTMLParser` subclass instead of a heavy DOM library: job
descriptions are well-formed enough, and this keeps the collector image free of
C extensions while giving full control over block boundaries and list bullets.
"""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser


_BLOCK_TAGS = {
    "p",
    "div",
    "section",
    "article",
    "header",
    "footer",
    "main",
    "aside",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "table",
    "thead",
    "tbody",
    "tr",
    "blockquote",
    "pre",
    "figure",
    "address",
}
_SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "iframe", "object"}
_TAG_RE = re.compile(r"<[^>]+>")
_SPACES_RE = re.compile(r"[ \t\f\v\u00a0\u202f]+")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "br":
            self._newline()
        elif tag == "li":
            self._newline()
            self.parts.append("• ")
        elif tag in _BLOCK_TAGS:
            self._newline()

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "br" and not self._skip_depth:
            self._newline()

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag in _BLOCK_TAGS or tag == "li":
            self._newline()

    def handle_data(self, data: str) -> None:
        if self._skip_depth or not data:
            return
        self.parts.append(data)

    def _newline(self) -> None:
        if self.parts and not self.parts[-1].endswith("\n"):
            self.parts.append("\n")


def _collapse(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    lines = [_SPACES_RE.sub(" ", line).strip() for line in text.split("\n")]
    cleaned = "\n".join(line for line in lines if line)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def html_to_text(value: str | None) -> str:
    """Strip tags and scripts, decode entities, keep paragraphs and list bullets."""
    if not value or not value.strip():
        return ""
    parser = _TextExtractor()
    try:
        parser.feed(value)
        parser.close()
    except Exception:  # pragma: no cover - HTMLParser is very tolerant
        return _collapse(html.unescape(_TAG_RE.sub(" ", value)))
    return _collapse("".join(parser.parts))


def truncate(text: str, limit: int) -> str:
    """Cut at a word boundary and mark the cut, for prompt budgets."""
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return f"{cut}…"
