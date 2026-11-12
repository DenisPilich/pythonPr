"""Bot entrypoint: wires middlewares and routers, then polls Telegram."""

from __future__ import annotations

import asyncio

import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import actions, jobs, profile, start, stats
from app.bot.middlewares import DbSessionMiddleware, ThrottlingMiddleware, UserMiddleware
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.db.session import Database


logger = structlog.get_logger(__name__)


def build_dispatcher(database: Database, *, throttle_interval: float = 0.4) -> Dispatcher:
    dispatcher = Dispatcher(storage=MemoryStorage())
    for observer in (dispatcher.message, dispatcher.callback_query):
        observer.middleware(DbSessionMiddleware(database))
        observer.middleware(UserMiddleware())
        observer.middleware(ThrottlingMiddleware(throttle_interval))
    dispatcher.include_routers(
        start.router,
        profile.router,
        jobs.router,
        stats.router,
        actions.router,
    )
    return dispatcher


async def run_bot(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    configure_logging(settings)
    if settings.telegram_bot_token is None:
        logger.warning(
            "bot_disabled", reason="TELEGRAM_BOT_TOKEN is not set; the API keeps running"
        )
        return

    database = Database(settings)
    bot = Bot(
        token=settings.telegram_bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dispatcher = build_dispatcher(database)
    logger.info("bot_starting", environment=settings.environment)
    try:
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        await bot.session.close()
        await database.dispose()
        logger.info("bot_stopped")


def main() -> int:
    asyncio.run(run_bot())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
