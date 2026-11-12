"""Telegram implementation of the `Notifier` port.

The message text is rendered by the notification service; the bot only attaches
the inline actions, so delivery and content stay independently testable.
"""

from __future__ import annotations

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, LinkPreviewOptions

from app.bot.keyboards import vacancy_actions
from app.core.config import Settings
from app.ports.vacancy_source import NotificationMessage, Notifier
from app.services.notification import LoggingNotifier


class TelegramNotifier:
    name = "telegram"

    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send_vacancy(self, message: NotificationMessage) -> int:
        keyboard: InlineKeyboardMarkup = vacancy_actions(message.vacancy_id, message.url)
        sent = await self._bot.send_message(
            chat_id=message.chat_id,
            text=message.text,
            reply_markup=keyboard,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
        return sent.message_id


def build_notifier(settings: Settings) -> Notifier:
    token = settings.telegram_bot_token
    if token is None:
        return LoggingNotifier()
    bot = Bot(
        token=token.get_secret_value(),
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    return TelegramNotifier(bot)
