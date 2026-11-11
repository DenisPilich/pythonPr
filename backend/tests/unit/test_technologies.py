from __future__ import annotations

from app.normalization.taxonomy import load_taxonomy
from app.normalization.technologies import TechnologyExtractor


EXTRACTOR = TechnologyExtractor(load_taxonomy())


def slugs(text: str) -> set[str]:
    return {mention.slug for mention in EXTRACTOR.extract(text)}


def test_finds_common_technologies() -> None:
    found = slugs("We build services with Python, FastAPI, PostgreSQL and Docker.")
    assert {"python", "fastapi", "postgresql", "docker"} <= found


def test_matches_aliases() -> None:
    assert {"postgresql", "kubernetes", "go"} <= slugs("postgres, k8s and golang")


def test_special_characters_are_matched() -> None:
    found = slugs("Experience with C++, C#, ASP.NET and Node.js is welcome")
    assert {"cpp", "csharp", "dotnet", "node"} <= found


def test_short_alias_does_not_match_inside_words() -> None:
    found = slugs("We go to market and its team is strong")
    assert "go" not in found
    assert "ts" not in found


def test_longest_alias_wins() -> None:
    found = slugs("React Native and React experience")
    assert "react_native" in found
    assert "react" in found


def test_counts_mentions() -> None:
    mentions = {m.slug: m.mentions for m in EXTRACTOR.extract("Python, python and PYTHON")}
    assert mentions["python"] == 3


def test_required_and_optional_sections() -> None:
    text = "Requirements: strong Python and Docker.\nNice to have: Kubernetes and Terraform."
    mentions = {m.slug: m.is_required for m in EXTRACTOR.extract(text)}
    assert mentions["python"] is True
    assert mentions["docker"] is True
    assert mentions["kubernetes"] is False
    assert mentions["terraform"] is False


def test_unknown_technology_is_ignored() -> None:
    assert slugs("We use Cobol and Fortran") == set()


def test_empty_text() -> None:
    assert EXTRACTOR.extract("") == ()
