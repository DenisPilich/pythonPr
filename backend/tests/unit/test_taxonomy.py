from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.domain.enums import TechnologyCategory
from app.normalization.taxonomy import (
    DEFAULT_TAXONOMY_PATH,
    TaxonomyError,
    load_taxonomy,
    parse_taxonomy,
)


def test_default_taxonomy_loads() -> None:
    taxonomy = load_taxonomy()
    assert taxonomy.version == 1
    assert len(taxonomy) >= 70
    assert Path(DEFAULT_TAXONOMY_PATH).is_file()


def test_every_technology_has_slug_name_and_aliases() -> None:
    taxonomy = load_taxonomy()
    for spec in taxonomy:
        assert spec.slug == spec.slug.lower()
        assert spec.name.strip()
        assert spec.aliases, f"{spec.slug} has no aliases"
        assert all(alias == alias.lower() for alias in spec.aliases)


def test_alias_index_is_globally_unique() -> None:
    taxonomy = load_taxonomy()
    index = taxonomy.alias_index()
    assert len(index) == sum(len(spec.aliases) for spec in taxonomy)
    assert index["postgres"] == "postgresql"
    assert index["k8s"] == "kubernetes"


def test_categories_come_from_enum() -> None:
    taxonomy = load_taxonomy()
    assert all(isinstance(spec.category, TechnologyCategory) for spec in taxonomy)


def test_unknown_slug_returns_none() -> None:
    assert load_taxonomy().get("cobol") is None


def payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "version": 1,
        "technologies": [
            {
                "slug": "python",
                "name": "Python",
                "category": "language",
                "aliases": ["python"],
            }
        ],
    }
    base.update(overrides)
    return base


def test_rejects_non_mapping_root() -> None:
    with pytest.raises(TaxonomyError):
        parse_taxonomy(["python"])


def test_rejects_missing_version() -> None:
    with pytest.raises(TaxonomyError):
        parse_taxonomy({"technologies": payload()["technologies"]})


def test_rejects_duplicate_alias_across_technologies() -> None:
    data = payload()
    data["technologies"].append(
        {
            "slug": "python3",
            "name": "Python 3",
            "category": "language",
            "aliases": ["python"],
        }
    )
    with pytest.raises(TaxonomyError, match="claimed by both"):
        parse_taxonomy(data)


def test_rejects_duplicate_slug() -> None:
    data = payload()
    data["technologies"].append(dict(data["technologies"][0]))
    with pytest.raises(TaxonomyError, match="duplicate technology slug"):
        parse_taxonomy(data)


@pytest.mark.parametrize("slug", ["Python", "-python", "python!", "1python"])
def test_rejects_invalid_slug(slug: str) -> None:
    data = payload()
    data["technologies"][0]["slug"] = slug
    with pytest.raises(TaxonomyError, match="slug is invalid"):
        parse_taxonomy(data)


def test_rejects_unknown_category() -> None:
    data = payload()
    data["technologies"][0]["category"] = "magic"
    with pytest.raises(TaxonomyError, match="category is invalid"):
        parse_taxonomy(data)


def test_rejects_empty_aliases() -> None:
    data = payload()
    data["technologies"][0]["aliases"] = []
    with pytest.raises(TaxonomyError, match="aliases"):
        parse_taxonomy(data)


def test_normalizes_alias_whitespace() -> None:
    data = payload()
    data["technologies"][0]["aliases"] = ["  Python  3 ", "python"]
    taxonomy = parse_taxonomy(data)
    assert taxonomy.technologies[0].aliases == ("python 3", "python")
