from __future__ import annotations

from datetime import UTC, datetime

from app.domain.dto import CollectedVacancy, SalaryInput
from app.domain.enums import SalaryPeriod, SeniorityLevel, VacancyLanguage, WorkFormat
from app.normalization.pipeline import NormalizationPipeline


PIPELINE = NormalizationPipeline()


def collected(**overrides: object) -> CollectedVacancy:
    values: dict[str, object] = {
        "source_code": "hh",
        "external_id": "123",
        "url": "https://hh.ru/vacancy/123",
        "title": "Senior Python Developer",
        "company_name": "Acme, Inc.",
        "description": "<p>We use Python, FastAPI, PostgreSQL and Docker.</p>",
        "location_raw": "Remote",
        "published_at": datetime(2026, 11, 1, tzinfo=UTC),
    }
    values.update(overrides)
    return CollectedVacancy(**values)  # type: ignore[arg-type]


def test_normalizes_all_fields() -> None:
    vacancy = PIPELINE.normalize(collected())

    assert vacancy.company_name == "Acme, Inc."
    assert vacancy.company_key == "acme"
    assert vacancy.work_format is WorkFormat.REMOTE
    assert vacancy.seniority is SeniorityLevel.SENIOR
    assert vacancy.language is VacancyLanguage.EN
    assert vacancy.description_clean.startswith("We use Python")
    assert {"python", "fastapi", "postgresql", "docker"} <= {
        mention.slug for mention in vacancy.technologies
    }
    assert vacancy.fingerprint
    assert vacancy.content_hash


def test_structured_salary_is_preferred() -> None:
    vacancy = PIPELINE.normalize(
        collected(salary=SalaryInput(60000, 80000, "EUR", SalaryPeriod.YEAR))
    )
    assert vacancy.salary is not None
    assert vacancy.salary.min == 60000
    assert vacancy.salary.period is SalaryPeriod.YEAR


def test_salary_text_is_parsed_when_no_structured_salary() -> None:
    vacancy = PIPELINE.normalize(collected(salary_text="€50k - €70k"))
    assert vacancy.salary is not None
    assert vacancy.salary.min == 50000
    assert vacancy.salary.currency == "EUR"


def test_fingerprint_is_stable_for_the_same_posting() -> None:
    first = PIPELINE.normalize(collected(external_id="1"))
    second = PIPELINE.normalize(collected(external_id="2"))
    assert first.fingerprint == second.fingerprint


def test_fingerprint_depends_on_location() -> None:
    remote = PIPELINE.normalize(collected())
    berlin = PIPELINE.normalize(collected(location_raw="Berlin, Germany"))
    assert remote.fingerprint != berlin.fingerprint


def test_content_hash_changes_when_description_changes() -> None:
    short = PIPELINE.normalize(collected(description="<p>Python</p>"))
    long = PIPELINE.normalize(collected(description="<p>Python and FastAPI</p>"))
    assert short.content_hash != long.content_hash
    assert short.fingerprint == long.fingerprint


def test_location_is_parsed() -> None:
    vacancy = PIPELINE.normalize(collected(location_raw="Berlin, Germany"))
    assert (vacancy.city, vacancy.country_code) == ("Berlin", "DE")
