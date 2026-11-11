"""Ingestion use case: normalized vacancy → database, idempotently.

Outcomes:
* `created`   — new fingerprint, vacancy + provenance + technologies inserted;
* `updated`   — known fingerprint, but the posting became richer (longer
  description, new salary, better classification);
* `duplicate` — known fingerprint, nothing changed; only `last_seen_at` moved.

Every outcome still refreshes provenance, which is what keeps a vacancy alive when
it is syndicated to another board.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.dto import NormalizedVacancy
from app.repositories.vacancies import VacancyRepository


IngestStatus = Literal["created", "updated", "duplicate"]


@dataclass(frozen=True, slots=True)
class IngestOutcome:
    status: IngestStatus
    vacancy_id: uuid.UUID
    technologies: int


class IngestService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = VacancyRepository(session)

    async def ingest(self, vacancy: NormalizedVacancy, source_id: uuid.UUID) -> IngestOutcome:
        company_id = await self._repo.get_or_create_company(
            vacancy.company_name, vacancy.company_key
        )
        existing = await self._repo.get_by_fingerprint(vacancy.fingerprint)

        if existing is None:
            created = await self._repo.insert_vacancy(vacancy, company_id)
            await self._repo.attach_source(created.id, source_id, vacancy)
            linked = await self._link_technologies(created.id, vacancy)
            return IngestOutcome(status="created", vacancy_id=created.id, technologies=linked)

        changed = self._repo.apply_update(existing, vacancy)
        await self._repo.attach_source(existing.id, source_id, vacancy)
        if not changed:
            return IngestOutcome(status="duplicate", vacancy_id=existing.id, technologies=0)

        linked = await self._link_technologies(existing.id, vacancy)
        await self._session.flush()
        return IngestOutcome(status="updated", vacancy_id=existing.id, technologies=linked)

    async def _link_technologies(self, vacancy_id: uuid.UUID, vacancy: NormalizedVacancy) -> int:
        slugs = [mention.slug for mention in vacancy.technologies]
        technology_ids = await self._repo.resolve_technology_ids(slugs)
        return await self._repo.replace_technologies(
            vacancy_id, vacancy.technologies, technology_ids
        )
