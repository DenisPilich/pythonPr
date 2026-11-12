"""`/history` — the user's tracked vacancies and status counts."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import PaginationDep, SessionDep, TelegramIdDep
from app.api.v1.mappers import job_to_list_item
from app.domain.enums import UserVacancyStatus
from app.repositories.history import HistoryRepository
from app.repositories.profiles import ProfileRepository
from app.schemas.history import HistoryCounts, HistoryItem, HistoryPage


router = APIRouter(prefix="/history", tags=["history"])


def _counts_payload(counts: dict[UserVacancyStatus, int]) -> HistoryCounts:
    return HistoryCounts(
        new=counts.get(UserVacancyStatus.NEW, 0),
        viewed=counts.get(UserVacancyStatus.VIEWED, 0),
        saved=counts.get(UserVacancyStatus.SAVED, 0),
        applied=counts.get(UserVacancyStatus.APPLIED, 0),
        rejected=counts.get(UserVacancyStatus.REJECTED, 0),
        total=sum(counts.values()),
    )


@router.get(
    "",
    response_model=HistoryPage,
    summary="User vacancy history",
    description=(
        "Returns tracked vacancies for `X-Telegram-Id` with their status, match score and "
        "per-status counts. An unknown user yields an empty page rather than 404."
    ),
)
async def get_history(
    session: SessionDep,
    telegram_id: TelegramIdDep,
    pagination: PaginationDep,
    status: Annotated[UserVacancyStatus | None, Query()] = None,
) -> HistoryPage:
    user = await ProfileRepository(session).get_user(telegram_id)
    if user is None:
        return HistoryPage(
            items=[],
            total=0,
            limit=pagination.limit,
            offset=pagination.offset,
            counts=HistoryCounts(),
        )

    repository = HistoryRepository(session)
    rows, total = await repository.list_for_user(
        user.id,
        status=status,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    counts = await repository.counts(user.id)
    return HistoryPage(
        items=[
            HistoryItem(
                job=job_to_list_item(vacancy),
                status=tracked.status,
                match_score=tracked.match_score,
                notified_at=tracked.notified_at,
                created_at=tracked.created_at,
            )
            for tracked, vacancy in rows
        ],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
        counts=_counts_payload(counts),
    )
