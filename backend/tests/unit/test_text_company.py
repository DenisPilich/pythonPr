from __future__ import annotations

from app.normalization.company import normalize_company
from app.normalization.text import html_to_text, truncate


def test_strips_scripts_styles_and_comments() -> None:
    html = "<style>.x{}</style><script>alert(1)</script><!-- note --><p>Hello <b>world</b></p>"
    assert html_to_text(html) == "Hello world"


def test_lists_become_bullets() -> None:
    assert html_to_text("<ul><li>Python</li><li>FastAPI</li></ul>") == "• Python\n• FastAPI"


def test_entities_are_decoded() -> None:
    assert html_to_text("<p>R&amp;D &lt;team&gt;</p>") == "R&D <team>"


def test_paragraphs_and_breaks() -> None:
    assert html_to_text("<p>One</p><p>Two</p>") == "One\nTwo"
    assert html_to_text("Line<br>Break") == "Line\nBreak"


def test_empty_and_none() -> None:
    assert html_to_text(None) == ""
    assert html_to_text("   ") == ""


def test_truncate_keeps_word_boundary() -> None:
    result = truncate("alpha beta gamma delta", 12)
    assert result.endswith("…")
    assert len(result) <= 13
    assert " " in result


def test_company_variants_share_key() -> None:
    keys = {normalize_company(name).key for name in ("Acme, Inc.", "ACME LLC", "Acme", "Acme Ltd.")}
    assert keys == {"acme"}


def test_company_display_preserves_casing_and_period() -> None:
    identity = normalize_company("  Acme,   Inc.  ")
    assert identity.display == "Acme, Inc."
    assert identity.key == "acme"


def test_company_strips_trailing_legal_suffixes() -> None:
    assert normalize_company("VK Group").key == "vk"
    assert normalize_company("Sberbank").key == "sberbank"


def test_company_handles_unicode_and_empty() -> None:
    assert normalize_company("Яндекс").key == "яндекс"
    assert normalize_company("   ").key == "unknown"
