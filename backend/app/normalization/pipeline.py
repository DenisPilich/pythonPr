"""Normalization pipeline: `CollectedVacancy` → `NormalizedVacancy`.

Every stage is total: a failure degrades to `unknown`/empty instead of raising,
because one malformed description must not abort a 200-vacancy collection run.
"""

from __future__ import annotations

from app.domain.dto import CollectedVacancy, NormalizedSalary, NormalizedVacancy
from app.normalization.company import normalize_company
from app.normalization.fingerprint import build_fingerprint, content_hash, location_key
from app.normalization.language import detect_language
from app.normalization.location import parse_location
from app.normalization.salary import normalize_salary, parse_salary_text
from app.normalization.seniority import detect_seniority
from app.normalization.taxonomy import Taxonomy
from app.normalization.technologies import TechnologyExtractor
from app.normalization.text import html_to_text
from app.normalization.work_format import detect_work_format


class NormalizationPipeline:
    def __init__(self, taxonomy: Taxonomy | None = None) -> None:
        self._extractor = TechnologyExtractor(taxonomy)

    def normalize(self, vacancy: CollectedVacancy) -> NormalizedVacancy:
        title = " ".join((vacancy.title or "").split())
        description_clean = html_to_text(vacancy.description)
        identity = normalize_company(vacancy.company_name)
        city, country_code = parse_location(vacancy.location_raw)
        work_format = detect_work_format(
            vacancy.location_raw, description_clean, vacancy.work_format_hint
        )

        salary: NormalizedSalary | None = normalize_salary(
            vacancy.salary or parse_salary_text(vacancy.salary_text)
        )

        location = location_key(city=city, country_code=country_code, work_format=work_format)
        fingerprint = build_fingerprint(identity.key, title, location=location)

        return NormalizedVacancy(
            source_code=vacancy.source_code,
            external_id=vacancy.external_id,
            url=vacancy.url,
            title=title,
            company_name=identity.display,
            company_key=identity.key,
            description_raw=vacancy.description,
            description_clean=description_clean,
            location_raw=vacancy.location_raw,
            city=city,
            country_code=country_code,
            work_format=work_format,
            seniority=detect_seniority(title, description_clean),
            language=detect_language(f"{title}\n{description_clean[:3000]}"),
            salary=salary,
            published_at=vacancy.published_at,
            technologies=self._extractor.extract(description_clean),
            fingerprint=fingerprint,
            content_hash=content_hash(description_clean or title),
            employment_type=vacancy.employment_type,
            raw_payload=vacancy.raw_payload,
        )
