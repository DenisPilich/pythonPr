"""Technology taxonomy: loading, validation and lookup.

The YAML file is the single source of truth for both the `technologies` table and
(stage 2) the extraction regex. Validation happens at load time so a typo fails a
test instead of silently producing wrong matches in production.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.domain.enums import TechnologyCategory


DEFAULT_TAXONOMY_PATH = Path(__file__).resolve().parent / "data" / "technologies.yml"

_SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
_MAX_ALIAS_LENGTH = 48


class TaxonomyError(ValueError):
    """Raised when the taxonomy document is malformed."""


@dataclass(frozen=True, slots=True)
class TechnologySpec:
    slug: str
    name: str
    category: TechnologyCategory
    aliases: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Taxonomy:
    version: int
    technologies: tuple[TechnologySpec, ...]

    def __len__(self) -> int:
        return len(self.technologies)

    def __iter__(self) -> Iterator[TechnologySpec]:
        return iter(self.technologies)

    def get(self, slug: str) -> TechnologySpec | None:
        return next((spec for spec in self.technologies if spec.slug == slug), None)

    @property
    def slugs(self) -> frozenset[str]:
        return frozenset(spec.slug for spec in self.technologies)

    def alias_index(self) -> dict[str, str]:
        """alias -> slug, for the future extraction matcher."""
        return {alias: spec.slug for spec in self.technologies for alias in spec.aliases}


def parse_taxonomy(payload: Any) -> Taxonomy:
    if not isinstance(payload, dict):
        raise TaxonomyError("taxonomy root must be a mapping")

    version = payload.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise TaxonomyError("`version` must be a positive integer")

    raw_items = payload.get("technologies")
    if not isinstance(raw_items, list) or not raw_items:
        raise TaxonomyError("`technologies` must be a non-empty list")

    specs: list[TechnologySpec] = []
    seen_slugs: set[str] = set()
    alias_owner: dict[str, str] = {}

    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            raise TaxonomyError(f"technologies[{index}] must be a mapping")

        slug = item.get("slug")
        name = item.get("name")
        raw_category = item.get("category")
        raw_aliases = item.get("aliases")

        if not isinstance(slug, str) or not _SLUG_PATTERN.match(slug):
            raise TaxonomyError(f"technologies[{index}].slug is invalid: {slug!r}")
        if slug in seen_slugs:
            raise TaxonomyError(f"duplicate technology slug: {slug!r}")
        if not isinstance(name, str) or not name.strip():
            raise TaxonomyError(f"technologies[{index}].name must be a non-empty string")

        if not isinstance(raw_category, str):
            raise TaxonomyError(f"technologies[{index}].category is invalid: {raw_category!r}")
        try:
            category = TechnologyCategory(raw_category)
        except ValueError as exc:
            raise TaxonomyError(
                f"technologies[{index}].category is invalid: {raw_category!r}"
            ) from exc

        if not isinstance(raw_aliases, list) or not raw_aliases:
            raise TaxonomyError(f"technologies[{index}].aliases must be a non-empty list")

        aliases: list[str] = []
        for raw_alias in raw_aliases:
            if not isinstance(raw_alias, str):
                raise TaxonomyError(f"technologies[{index}].aliases must contain strings")
            alias = " ".join(raw_alias.lower().split())
            if not alias or len(alias) > _MAX_ALIAS_LENGTH:
                raise TaxonomyError(
                    f"technologies[{index}] has an empty or overlong alias: {raw_alias!r}"
                )
            previous_owner = alias_owner.get(alias)
            if previous_owner is not None and previous_owner != slug:
                raise TaxonomyError(
                    f"alias {alias!r} is claimed by both {previous_owner!r} and {slug!r}"
                )
            alias_owner[alias] = slug
            if alias not in aliases:
                aliases.append(alias)

        seen_slugs.add(slug)
        specs.append(
            TechnologySpec(
                slug=slug,
                name=name.strip(),
                category=category,
                aliases=tuple(aliases),
            )
        )

    return Taxonomy(version=version, technologies=tuple(specs))


def load_taxonomy(path: Path | None = None) -> Taxonomy:
    taxonomy_path = path or DEFAULT_TAXONOMY_PATH
    try:
        with taxonomy_path.open("r", encoding="utf-8") as handle:
            payload: Any = yaml.safe_load(handle)
    except OSError as exc:
        raise TaxonomyError(f"cannot read taxonomy at {taxonomy_path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise TaxonomyError(f"invalid YAML in {taxonomy_path}: {exc}") from exc
    return parse_taxonomy(payload)
