"""Technology extraction from a curated taxonomy.

One compiled alternation over all aliases, longest alias first, with word
boundaries that do not break `.NET`, `C#`, `C++` or `Node.js`. A vacancy usually
mentions 5–15 technologies; counting mentions lets the dashboard rank demand and
lets the AI prompt highlight what the role actually revolves around.
"""

from __future__ import annotations

import re

from app.domain.dto import TechnologyMention
from app.normalization.taxonomy import Taxonomy, load_taxonomy


_REQUIREMENT_MARKERS = re.compile(
    r"(requirements?|qualifications?|must[- ]have|what you(?:'|’)ll need|what we expect|"
    r"требования|ожидания|что мы ждем|что нужно)",
    re.IGNORECASE,
)
_REQUIREMENT_WINDOW = 2500
_OPTIONAL_MARKERS = re.compile(
    r"(nice[- ]to[- ]have|bonus points|advantage|preferred|желательно|будет плюсом)",
    re.IGNORECASE,
)
_OPTIONAL_WINDOW = 400


class TechnologyExtractor:
    """Stateless extractor; build once per process and reuse."""

    def __init__(self, taxonomy: Taxonomy | None = None) -> None:
        taxonomy = taxonomy or load_taxonomy()
        pairs = [(alias, spec.slug) for spec in taxonomy.technologies for alias in spec.aliases]
        pairs.sort(key=lambda pair: len(pair[0]), reverse=True)
        self._alias_to_slug: dict[str, str] = dict(pairs)
        self._pattern = re.compile(
            "|".join(self._alias_pattern(alias) for alias, _ in pairs),
            re.IGNORECASE,
        )

    @staticmethod
    def _alias_pattern(alias: str) -> str:
        escaped = re.escape(alias)
        prefix = r"(?<![\w])" if alias[:1].isalnum() else ""
        suffix = r"(?![\w])" if alias[-1:].isalnum() else ""
        return f"{prefix}{escaped}{suffix}"

    @staticmethod
    def _requirement_windows(text: str) -> list[tuple[int, int]]:
        return [
            (match.end(), match.end() + _REQUIREMENT_WINDOW)
            for match in _REQUIREMENT_MARKERS.finditer(text)
        ]

    @staticmethod
    def _optional_windows(text: str) -> list[tuple[int, int]]:
        return [
            (match.end(), match.end() + _OPTIONAL_WINDOW)
            for match in _OPTIONAL_MARKERS.finditer(text)
        ]

    def extract(self, text: str) -> tuple[TechnologyMention, ...]:
        if not text:
            return ()

        required_windows = self._requirement_windows(text)
        optional_windows = self._optional_windows(text)
        counts: dict[str, int] = {}
        required: set[str] = set()

        for match in self._pattern.finditer(text):
            alias = " ".join(match.group(0).lower().split())
            slug = self._alias_to_slug.get(alias)
            if slug is None:  # pragma: no cover - every alternative is mapped
                continue
            counts[slug] = counts.get(slug, 0) + 1
            in_requirements = any(start <= match.start() <= end for start, end in required_windows)
            in_optional = any(start <= match.start() <= end for start, end in optional_windows)
            if in_requirements and not in_optional:
                required.add(slug)

        ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return tuple(
            TechnologyMention(slug=slug, is_required=slug in required, mentions=count)
            for slug, count in ordered
        )


def default_extractor() -> TechnologyExtractor:
    return TechnologyExtractor(load_taxonomy())
