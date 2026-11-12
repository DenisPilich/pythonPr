"""`/stats`: global radar statistics plus the user's own history."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import services, texts
from app.models import User
from app.services.stats import StatsService


router = Router(name="stats")


async def _stats_text(session: AsyncSession, db_user: User) -> str:
    stats = await StatsService(session, redis=None, cache_enabled=False).overview()
    personal = await services.personal_stats(session, db_user.id)
    return texts.stats_text(stats, personal.as_dict())


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession, db_user: User) -> None:
    await message.answer(await _stats_text(session, db_user))


@router.callback_query(F.data == "menu:stats")
async def menu_stats(callback: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    text = await _stats_text(session, db_user)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text)
    await callback.answer()
