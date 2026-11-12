"""Inline actions on a vacancy: save, applied, skip."""

from __future__ import annotations

import uuid

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import services
from app.models import User


router = Router(name="actions")

_ANSWERS = {
    "save": "Сохранено",
    "applied": "Отмечено как Applied",
    "skip": "Скрыто",
}


@router.callback_query(F.data.startswith("vac:"))
async def vacancy_action(callback: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    parts = (callback.data or "").split(":")
    if len(parts) != 3:
        await callback.answer("Некорректная кнопка", show_alert=True)
        return

    action, raw_id = parts[1], parts[2]
    try:
        vacancy_id = uuid.UUID(raw_id)
    except ValueError:
        await callback.answer("Некорректная вакансия", show_alert=True)
        return

    status = await services.apply_vacancy_action(
        session, user_id=db_user.id, vacancy_id=vacancy_id, action=action
    )
    if status is None:
        await callback.answer("Действие недоступно", show_alert=True)
        return

    await callback.answer(_ANSWERS.get(action, "Готово"))
