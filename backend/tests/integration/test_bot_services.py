from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import services
from app.domain.enums import UserVacancyStatus
from app.models import UserVacancy
from tests.integration.test_analysis_service import create_profile, create_vacancy


pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("taxonomy_rows")]


async def test_update_profile_merges_one_field(db_session: AsyncSession) -> None:
    user, original = await create_profile(db_session)
    original_hash = original.profile_hash
    original_formats = list(original.work_formats)

    updated = await services.update_profile(
        db_session,
        telegram_id=user.telegram_id,
        user_id=user.id,
        skills=["Go", "Rust"],
    )

    assert updated.skills == ["Go", "Rust"]
    assert updated.work_formats == original_formats
    assert updated.profile_hash != original_hash


async def test_ensure_profile_creates_empty_profile(db_session: AsyncSession) -> None:
    profile = await services.ensure_profile(db_session, 9100)

    assert profile.user_id is not None
    assert profile.skills == []
    assert profile.min_match_score == 70


async def test_vacancy_actions_follow_allowed_transitions(
    db_session: AsyncSession,
) -> None:
    user, _ = await create_profile(db_session)
    vacancy = await create_vacancy(db_session)
    db_session.add(
        UserVacancy(
            user_id=user.id,
            vacancy_id=vacancy.id,
            status=UserVacancyStatus.NEW,
            match_score=90,
        )
    )
    await db_session.flush()

    assert (
        await services.apply_vacancy_action(
            db_session, user_id=user.id, vacancy_id=vacancy.id, action="save"
        )
        is UserVacancyStatus.SAVED
    )
    assert (
        await services.apply_vacancy_action(
            db_session, user_id=user.id, vacancy_id=vacancy.id, action="applied"
        )
        is UserVacancyStatus.APPLIED
    )
    assert (
        await services.apply_vacancy_action(
            db_session, user_id=user.id, vacancy_id=vacancy.id, action="skip"
        )
        is None
    )


async def test_vacancy_action_rejects_unknown_vacancy(db_session: AsyncSession) -> None:
    user, _ = await create_profile(db_session)

    result = await services.apply_vacancy_action(
        db_session, user_id=user.id, vacancy_id=uuid.uuid4(), action="save"
    )

    assert result is None


async def test_list_and_personal_stats(db_session: AsyncSession) -> None:
    user, _ = await create_profile(db_session)
    vacancy = await create_vacancy(db_session)
    db_session.add(
        UserVacancy(
            user_id=user.id,
            vacancy_id=vacancy.id,
            status=UserVacancyStatus.APPLIED,
            match_score=88,
        )
    )
    await db_session.flush()

    rows = await services.list_user_vacancies(db_session, user.id)
    stats = await services.personal_stats(db_session, user.id)

    assert len(rows) == 1
    assert rows[0][1].title == "Senior Python Developer"
    assert stats.applied == 1
    assert stats.sent == 1
    assert stats.viewed == 0


async def test_get_profile_returns_none_for_unknown_user(
    db_session: AsyncSession,
) -> None:
    assert await services.get_profile(db_session, uuid.uuid4()) is None
