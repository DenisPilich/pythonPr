from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.bot.notifier import TelegramNotifier
from app.ports.vacancy_source import NotificationMessage


class FakeBot:
    def __init__(self) -> None:
        self.kwargs: dict[str, object] | None = None

    async def send_message(self, **kwargs: object) -> SimpleNamespace:
        self.kwargs = kwargs
        return SimpleNamespace(message_id=42)


async def test_notifier_sends_message_with_actions() -> None:
    bot = FakeBot()
    notifier = TelegramNotifier(bot)  # type: ignore[arg-type]
    vacancy_id = uuid.uuid4()

    message_id = await notifier.send_vacancy(
        NotificationMessage(
            chat_id=777,
            text="<b>Senior Python Developer</b>",
            vacancy_id=vacancy_id,
            url="https://example.com/jobs/1",
        )
    )

    assert message_id == 42
    assert bot.kwargs is not None
    assert bot.kwargs["chat_id"] == 777
    assert bot.kwargs["parse_mode"] == "HTML"
    keyboard = bot.kwargs["reply_markup"]
    rows = keyboard.inline_keyboard  # type: ignore[union-attr]
    assert rows[0][0].url == "https://example.com/jobs/1"
    callbacks = {button.callback_data for button in rows[1]}
    assert f"vac:save:{vacancy_id}" in callbacks
    assert f"vac:applied:{vacancy_id}" in callbacks
    assert f"vac:skip:{vacancy_id}" in callbacks


def test_logging_notifier_is_used_without_token() -> None:
    from app.bot.notifier import build_notifier
    from app.core.config import Settings

    notifier = build_notifier(Settings(_env_file=None, telegram_bot_token=None))

    assert notifier.__class__.__name__ == "LoggingNotifier"
