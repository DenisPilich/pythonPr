"""Vacancy persistence: company resolution, provenance, technology links.

The repository owns SQL; the ingest service owns the decision "create, update or
leave alone". Keeping that split makes the dedup policy testable without mocking
SQLAlchemy internals.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.dto import NormalizedSalary, NormalizedVacancy, TechnologyMention
from app.domain.enums import SalaryPeriod, SeniorityLevel, VacancyLanguage, WorkFormat
from app.models import Company, Technology, Vacancy, VacancySource, VacancyTechnology


class VacancyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- lookup ----------------------------------------------------------
    async def get_or_create_company(self, display_name: str, key: str) -> uuid.UUID:
        await self._session.execute(
            pg_insert(Company)
            .values(name=display_name, normalized_name=key)
            .on_conflict_do_nothing(index_elements=[Company.normalized_name])
        )
        company_id = await self._session.scalar(
            select(Company.id).where(Company.normalized_name == key)
        )
        if company_id is None:  # pragma: no cover - insert or select must win
            raise RuntimeError(f"company {key!r} disappeared during upsert")
        return company_id

    async def resolve_technology_ids(self, slugs: list[str]) -> dict[str, uuid.UUID]:
        if not slugs:
            return {}
        rows = await self._session.execute(
            select(Technology.slug, Technology.id).where(Technology.slug.in_(slugs))
        )
        return dict(rows.all())

    async def get_by_fingerprint(self, fingerprint: str) -> Vacancy | None:
        return await self._session.scalar(select(Vacancy).where(Vacancy.fingerprint == fingerprint))

    # --- writes ----------------------------------------------------------
    async def insert_vacancy(self, vacancy: NormalizedVacancy, company_id: uuid.UUID) -> Vacancy:
        now = datetime.now(UTC)
        salary = vacancy.salary
        entity = Vacancy(
            company_id=company_id,
            title=vacancy.title,
            description_raw=vacancy.description_raw,
            description_clean=vacancy.description_clean,
            salary_min=salary.min if salary else None,
            salary_max=salary.max if salary else None,
            salary_currency=salary.currency if salary else None,
            salary_period=salary.period if salary else SalaryPeriod.UNKNOWN,
            salary_is_estimated=salary.is_estimated if salary else False,
            salary_monthly_eur=salary.monthly_eur if salary else None,
            location_raw=vacancy.location_raw,
            city=vacancy.city,
            country_code=vacancy.country_code,
            work_format=vacancy.work_format,
            seniority=vacancy.seniority,
            language=vacancy.language,
            published_at=vacancy.published_at,
            first_seen_at=now,
            last_seen_at=now,
            fingerprint=vacancy.fingerprint,
            content_hash=vacancy.content_hash,
            is_active=True,
        )
        self._session.add(entity)
        await self._session.flush()
        return entity

    def apply_update(self, vacancy: Vacancy, incoming: NormalizedVacancy) -> bool:
        """Merge a re-observed vacancy; returns True when the content changed."""
        changed = False
        vacancy.last_seen_at = datetime.now(UTC)
        if not vacancy.is_active:
            vacancy.is_active = True
            changed = True

        if len(incoming.description_clean) > len(vacancy.description_clean):
            vacancy.description_raw = incoming.description_raw
            vacancy.description_clean = incoming.description_clean
            vacancy.content_hash = incoming.content_hash
            vacancy.title = incoming.title
            changed = True

        if incoming.salary is not None:
            salary: NormalizedSalary = incoming.salary
            if (
                vacancy.salary_min != salary.min
                or vacancy.salary_max != salary.max
                or vacancy.salary_currency != salary.currency
            ):
                vacancy.salary_min = salary.min
                vacancy.salary_max = salary.max
                vacancy.salary_currency = salary.currency
                vacancy.salary_period = salary.period
                vacancy.salary_is_estimated = salary.is_estimated
                vacancy.salary_monthly_eur = salary.monthly_eur
                changed = True

        if (
            incoming.work_format is not WorkFormat.UNKNOWN
            and vacancy.work_format is not incoming.work_format
        ):
            vacancy.work_format = incoming.work_format
            changed = True
        if (
            incoming.seniority is not SeniorityLevel.UNKNOWN
            and vacancy.seniority is not incoming.seniority
        ):
            vacancy.seniority = incoming.seniority
            changed = True
        if (
            incoming.language is not VacancyLanguage.UNKNOWN
            and vacancy.language is not incoming.language
        ):
            vacancy.language = incoming.language
            changed = True

        if incoming.city and not vacancy.city:
            vacancy.city = incoming.city
        if incoming.country_code and not vacancy.country_code:
            vacancy.country_code = incoming.country_code
        if incoming.published_at and not vacancy.published_at:
            vacancy.published_at = incoming.published_at
        return changed

    async def attach_source(
        self,
        vacancy_id: uuid.UUID,
        source_id: uuid.UUID,
        vacancy: NormalizedVacancy,
    ) -> None:
        now = datetime.now(UTC)
        await self._session.execute(
            pg_insert(VacancySource)
            .values(
                vacancy_id=vacancy_id,
                source_id=source_id,
                external_id=vacancy.external_id,
                url=vacancy.url,
                raw_payload=vacancy.raw_payload,
                first_seen_at=now,
                last_seen_at=now,
            )
            .on_conflict_do_update(
                index_elements=[VacancySource.source_id, VacancySource.external_id],
                set_={
                    "vacancy_id": vacancy_id,
                    "url": vacancy.url,
                    "raw_payload": vacancy.raw_payload,
                    "last_seen_at": now,
                },
            )
        )

    async def replace_technologies(
        self,
        vacancy_id: uuid.UUID,
        mentions: tuple[TechnologyMention, ...],
        technology_ids: dict[str, uuid.UUID],
    ) -> int:
        await self._session.execute(
            delete(VacancyTechnology).where(VacancyTechnology.vacancy_id == vacancy_id)
        )
        rows = [
            {
                "vacancy_id": vacancy_id,
                "technology_id": technology_ids[mention.slug],
                "is_required": mention.is_required,
                "mentions": mention.mentions,
            }
            for mention in mentions
            if mention.slug in technology_ids
        ]
        if rows:
            await self._session.execute(pg_insert(VacancyTechnology).values(rows))
        return len(rows)
