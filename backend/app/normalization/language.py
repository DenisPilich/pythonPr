"""Language detection without a model file.

Script detection decides Cyrillic vs Latin; a small stop-word vote separates
English, German, Polish, Spanish and Ukrainian. This is deterministic, fast and
dependency-free — good enough to choose the right prompt language and to filter
vacancies the user cannot read. A statistical detector is a documented upgrade
path, not a requirement.
"""

from __future__ import annotations

import re

from app.domain.enums import VacancyLanguage


_CYRILLIC_RE = re.compile(r"[а-яёА-ЯЁ]")
_LATIN_RE = re.compile(r"[a-zA-ZÀ-ÿ]")
_WORD_RE = re.compile(r"[a-zA-ZÀ-ÿ]+")
_UKRAINIAN_LETTERS = frozenset("іїєґІЇЄҐ")

_STOPWORDS: dict[VacancyLanguage, frozenset[str]] = {
    VacancyLanguage.EN: frozenset(
        [
            "the",
            "and",
            "with",
            "for",
            "you",
            "we",
            "are",
            "our",
            "will",
            "have",
            "this",
            "from",
            "your",
            "that",
            "not",
            "experience",
            "team",
            "work",
            "role",
            "looking",
        ]
    ),
    VacancyLanguage.DE: frozenset(
        [
            "und",
            "der",
            "die",
            "das",
            "mit",
            "für",
            "sie",
            "wir",
            "ist",
            "im",
            "den",
            "zu",
            "ein",
            "eine",
            "als",
            "auch",
            "sowie",
            "suchen",
            "einen",
            "entwickler",
            "entwicklerin",
            "kenntnisse",
            "erfahrungen",
            "bewerben",
            "aufgaben",
            "profil",
        ]
    ),
    VacancyLanguage.PL: frozenset(
        [
            "i",
            "w",
            "z",
            "na",
            "do",
            "nie",
            "jest",
            "się",
            "dla",
            "oraz",
            "jak",
            "co",
            "kandydat",
            "wymagania",
            "oferujemy",
            "praca",
            "szukamy",
            "programisty",
            "doświadczenie",
            "znajomość",
            "lub",
            "będzie",
            "zespołu",
        ]
    ),
    VacancyLanguage.ES: frozenset(
        [
            "y",
            "de",
            "la",
            "el",
            "en",
            "que",
            "con",
            "para",
            "los",
            "las",
            "una",
            "del",
            "por",
            "como",
            "experiencia",
            "buscamos",
            "conocimientos",
            "trabajo",
            "remoto",
            "equipo",
            "desarrollo",
        ]
    ),
}


def _latin_language(text: str) -> VacancyLanguage:
    words = _WORD_RE.findall(text.lower())
    if len(words) < 3:
        return VacancyLanguage.EN

    scores = {
        language: sum(1 for word in words if word in stopwords)
        for language, stopwords in _STOPWORDS.items()
    }
    best_language, best_score = max(scores.items(), key=lambda item: item[1])
    runner_up = sorted(scores.values())[-2] if len(scores) > 1 else 0
    if best_score >= 2 and best_score > runner_up:
        return best_language
    return VacancyLanguage.EN


def detect_language(text: str) -> VacancyLanguage:
    sample = text[:4000]
    if not sample.strip():
        return VacancyLanguage.UNKNOWN

    cyrillic = len(_CYRILLIC_RE.findall(sample))
    latin = len(_LATIN_RE.findall(sample))
    total = cyrillic + latin
    if total == 0:
        return VacancyLanguage.UNKNOWN

    if cyrillic / total >= 0.3:
        if any(letter in _UKRAINIAN_LETTERS for letter in sample):
            return VacancyLanguage.UK
        return VacancyLanguage.RU
    if latin / total >= 0.5:
        return _latin_language(sample)
    return VacancyLanguage.OTHER
