from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from aiogram.methods import SendMessage
from aiogram.types import CallbackQuery, Chat, Message, Update
from aiogram.types import User as TelegramUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.main import build_dispatcher
from app.domain.enums import UserVacancyStatus
from app.models import User, UserVacancy
from tests.integration.test_analysis_service import create_vacancy


pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("taxonomy_rows")]

CHAT_ID = 101


class FakeBot:
    id = 1

    def __init__(self) -> None:
        self.requests: list[Any] = []

    async def __call__(self, method: Any, **kwargs: Any) -> Message:
        self.requests.append(method)
        return Message(
            message_id=len(self.requests),
            date=datetime.now(UTC),
            chat=Chat(id=CHAT_ID, type="private"),
            text=getattr(method, "text", None),
        )


def telegram_user() -> TelegramUser:
    return TelegramUser(id=CHAT_ID, is_bot=False, first_name="Denis", username="denis")


def message(bot: FakeBot, text: str) -> Message:
    return Message(
        message_id=1,
        date=datetime.now(UTC),
        chat=Chat(id=CHAT_ID, type="private"),
        from_user=telegram_user(),
        text=text,
    ).as_(bot)


async def test_start_then_vacancy_action_callback(
    db_session: AsyncSession, stub_database: Any
) -> None:
    bot = FakeBot()
    dispatcher = build_dispatcher(stub_database, throttle_interval=0)

    await dispatcher.feed_update(bot, Update(update_id=1, message=message(bot, "/start")))

    user = await db_session.scalar(select(User).where(User.telegram_id == CHAT_ID))
    assert user is not None
    sent = [request for request in bot.requests if isinstance(request, SendMessage)]
    assert sent
    assert "AI Job Radar" in (sent[0].text or "")

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

    callback = CallbackQuery(
        id="callback-1",
        from_user=telegram_user(),
        chat_instance="chat-instance",
        message=message(bot, "vacancy card"),
        data=f"vac:save:{vacancy.id}",
    )
    await dispatcher.feed_update(bot, Update(update_id=2, callback_query=callback))

    tracked = await db_session.scalar(
        select(UserVacancy)
        .where(UserVacancy.user_id == user.id, UserVacancy.vacancy_id == vacancy.id)
        .execution_options(populate_existing=True)
    )
    assert tracked is not None
    assert tracked.status is UserVacancyStatus.SAVED
