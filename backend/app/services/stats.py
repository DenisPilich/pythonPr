"""Dashboard statistics with a short-lived Redis cache.

Statistics are read far more often than the underlying data changes, so the whole
response is cached for 60 seconds. Redis is best-effort: if it is down the API
still answers, only slower — an `AppError` here would turn a cache outage into a
dashboard outage.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Vacancy
from app.repositories.stats import StatsRepository
from app.schemas.stats import (
    AnalysisSummary,
    CollectorRunsSummary,
    CompanyStat,
    DistributionItem,
    SourceStat,
    StatsResponse,
    TechnologyStat,
    VacancyTotals,
)


logger = structlog.get_logger(__name__)

CACHE_KEY = "stats:overview:v1"
CACHE_TTL_SECONDS = 60


def _share(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


class StatsService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        redis: Redis | None = None,
        cache_enabled: bool = True,
    ) -> None:
        self._repository = StatsRepository(session)
        self._redis = redis
        self._cache_enabled = cache_enabled and redis is not None

    async def overview(self) -> StatsResponse:
        if self._cache_enabled:
            cached = await self._read_cache()
            if cached is not None:
                return cached

        response = await self._build()
        if self._cache_enabled:
            await self._write_cache(response)
        return response

    async def _read_cache(self) -> StatsResponse | None:
        assert self._redis is not None
        try:
            payload = await self._redis.get(CACHE_KEY)
        except Exception as exc:
            logger.warning("stats_cache_read_failed", error=type(exc).__name__)
            return None
        if not payload:
            return None
        try:
            return StatsResponse.model_validate_json(payload)
        except ValueError:
            return None

    async def _write_cache(self, response: StatsResponse) -> None:
        assert self._redis is not None
        try:
            await self._redis.setex(CACHE_KEY, CACHE_TTL_SECONDS, response.model_dump_json())
        except Exception as exc:
            logger.warning("stats_cache_write_failed", error=type(exc).__name__)

    async def _build(self) -> StatsResponse:
        totals = await self._repository.vacancy_totals()
        seniority = await self._repository.distribution(Vacancy.seniority)
        work_formats = await self._repository.distribution(Vacancy.work_format)
        languages = await self._repository.distribution(Vacancy.language)
        technologies = await self._repository.top_technologies(limit=10)
        companies = await self._repository.top_companies(limit=8)
        sources = await self._repository.sources_health()
        analyses = await self._repository.analysis_summary()
        runs = await self._repository.run_summary()

        return StatsResponse(
            generated_at=datetime.now(UTC),
            vacancies=VacancyTotals(
                total=totals.total,
                active=totals.active,
                with_salary=totals.with_salary,
                new_last_7_days=totals.new_last_7_days,
                remote=totals.remote,
                remote_share=_share(totals.remote, totals.total),
            ),
            sources=[
                SourceStat(
                    code=source.code,
                    name=source.name,
                    is_enabled=source.is_enabled,
                    vacancies=source.vacancies,
                    last_success_at=source.last_success_at,
                    last_run_status=source.last_run_status,
                )
                for source in sources
            ],
            top_technologies=[
                TechnologyStat(
                    slug=item.slug,
                    name=item.name,
                    count=item.count,
                    share=_share(item.count, totals.total),
                )
                for item in technologies
            ],
            top_companies=[
                CompanyStat(id=item.id, name=item.name, count=item.count) for item in companies
            ],
            seniority=[
                DistributionItem(
                    key=item.key, count=item.count, share=_share(item.count, totals.total)
                )
                for item in seniority
            ],
            work_formats=[
                DistributionItem(
                    key=item.key, count=item.count, share=_share(item.count, totals.total)
                )
                for item in work_formats
            ],
            languages=[
                DistributionItem(
                    key=item.key, count=item.count, share=_share(item.count, totals.total)
                )
                for item in languages
            ],
            analyses=AnalysisSummary(
                analyses=analyses.analyses,
                average_match_score=analyses.average_score,
            ),
            collector_runs=CollectorRunsSummary(
                last_24h=runs.last_24h,
                failed_last_24h=runs.failed_last_24h,
                last_status=runs.last_status,
            ),
        )
