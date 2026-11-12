"""`/profile`, `/settings` and the whole profile editor."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import services, texts
from app.bot.keyboards import (
    create_profile_keyboard,
    format_menu,
    main_menu,
    profile_menu,
    seniority_menu,
    settings_menu,
    threshold_menu,
)
from app.bot.states import ProfileEdit
from app.domain.enums import SeniorityLevel, WorkFormat
from app.models import User, UserProfile


router = Router(name="profile")


async def _show_profile(callback: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    profile = await services.get_profile(session, db_user.id)
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    if profile is None:
        await callback.message.edit_text(
            texts.profile_missing_text(), reply_markup=create_profile_keyboard()
        )
    else:
        await callback.message.edit_text(texts.profile_text(profile), reply_markup=profile_menu())
    await callback.answer()


async def _show_settings(callback: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    profile = await services.get_profile(session, db_user.id)
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    if profile is None:
        await callback.message.edit_text(
            texts.profile_missing_text(), reply_markup=create_profile_keyboard()
        )
    else:
        await callback.message.edit_text(
            texts.settings_text(profile), reply_markup=settings_menu(profile)
        )
    await callback.answer()


@router.message(Command("profile"))
async def cmd_profile(message: Message, session: AsyncSession, db_user: User) -> None:
    profile = await services.get_profile(session, db_user.id)
    if profile is None:
        await message.answer(texts.profile_missing_text(), reply_markup=create_profile_keyboard())
        return
    await message.answer(texts.profile_text(profile), reply_markup=profile_menu())


@router.message(Command("settings"))
async def cmd_settings(message: Message, session: AsyncSession, db_user: User) -> None:
    profile = await services.get_profile(session, db_user.id)
    if profile is None:
        await message.answer(texts.profile_missing_text(), reply_markup=create_profile_keyboard())
        return
    await message.answer(texts.settings_text(profile), reply_markup=settings_menu(profile))


@router.callback_query(F.data == "menu:profile")
async def menu_profile(callback: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    await _show_profile(callback, session, db_user)


@router.callback_query(F.data == "menu:settings")
async def menu_settings(callback: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    await _show_settings(callback, session, db_user)


@router.callback_query(F.data == "profile:create")
async def create_profile(callback: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    profile = await services.ensure_profile(session, db_user.telegram_id)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(texts.profile_text(profile), reply_markup=profile_menu())
    await callback.answer("Профиль создан")


# --- FSM editors -----------------------------------------------------------


@router.callback_query(F.data == "profile:edit:skills")
async def ask_skills(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProfileEdit.skills)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "Пришли навыки через запятую, например:\nPython, FastAPI, PostgreSQL, Docker"
        )
    await callback.answer()


@router.callback_query(F.data == "profile:edit:stack")
async def ask_stack(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProfileEdit.stack)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "Какой стек тебе интересен? Через запятую:\nFastAPI, PostgreSQL, Redis"
        )
    await callback.answer()


@router.callback_query(F.data == "profile:edit:salary")
async def ask_salary(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProfileEdit.salary)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "Напиши минимальную зарплату и валюту, например:\n3000 EUR"
        )
    await callback.answer()


@router.message(ProfileEdit.skills, F.text)
async def save_skills(
    message: Message, state: FSMContext, session: AsyncSession, db_user: User
) -> None:
    items = services.parse_list(message.text or "")
    if not items:
        await message.answer("Не понял. Пришли хотя бы один навык через запятую.")
        return
    profile = await services.update_profile(
        session, telegram_id=db_user.telegram_id, user_id=db_user.id, skills=items
    )
    await state.clear()
    await message.answer(
        "✅ Навыки обновлены.\n\n" + texts.profile_text(profile),
        reply_markup=profile_menu(),
    )


@router.message(ProfileEdit.stack, F.text)
async def save_stack(
    message: Message, state: FSMContext, session: AsyncSession, db_user: User
) -> None:
    items = services.parse_list(message.text or "")
    if not items:
        await message.answer("Не понял. Пришли стек через запятую.")
        return
    profile = await services.update_profile(
        session,
        telegram_id=db_user.telegram_id,
        user_id=db_user.id,
        preferred_stack=items,
    )
    await state.clear()
    await message.answer(
        "✅ Стек обновлён.\n\n" + texts.profile_text(profile),
        reply_markup=profile_menu(),
    )


@router.message(ProfileEdit.salary, F.text)
async def save_salary(
    message: Message, state: FSMContext, session: AsyncSession, db_user: User
) -> None:
    parsed = services.parse_salary(message.text or "")
    if parsed is None:
        await message.answer("Не понял. Пример: 3000 EUR")
        return
    amount, currency = parsed
    profile = await services.update_profile(
        session,
        telegram_id=db_user.telegram_id,
        user_id=db_user.id,
        min_salary_amount=amount,
        salary_currency=currency,
    )
    await state.clear()
    await message.answer(
        "✅ Зарплата обновлена.\n\n" + texts.profile_text(profile),
        reply_markup=profile_menu(),
    )


# --- one-tap settings ------------------------------------------------------


@router.callback_query(F.data == "profile:edit:seniority")
async def choose_seniority(callback: CallbackQuery) -> None:
    if isinstance(callback.message, Message):
        await callback.message.edit_text("Какой уровень искать?", reply_markup=seniority_menu())
    await callback.answer()


@router.callback_query(F.data == "profile:edit:format")
async def choose_format(callback: CallbackQuery) -> None:
    if isinstance(callback.message, Message):
        await callback.message.edit_text("Какой формат работы?", reply_markup=format_menu())
    await callback.answer()


@router.callback_query(F.data == "profile:edit:threshold")
async def choose_threshold(callback: CallbackQuery) -> None:
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "При каком совпадении присылать вакансию?", reply_markup=threshold_menu()
        )
    await callback.answer()


@router.callback_query(F.data.startswith("profile:set:seniority:"))
async def set_seniority(callback: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    raw = (callback.data or "").rsplit(":", 1)[-1]
    try:
        level = SeniorityLevel(raw)
    except ValueError:
        await callback.answer("Неизвестный уровень", show_alert=True)
        return
    profile = await services.update_profile(
        session,
        telegram_id=db_user.telegram_id,
        user_id=db_user.id,
        target_seniority=[level],
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(texts.profile_text(profile), reply_markup=profile_menu())
    await callback.answer(f"Уровень: {level.value}")


@router.callback_query(F.data.startswith("profile:set:format:"))
async def set_format(callback: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    raw = (callback.data or "").rsplit(":", 1)[-1]
    try:
        fmt = WorkFormat(raw)
    except ValueError:
        await callback.answer("Неизвестный формат", show_alert=True)
        return
    profile = await services.update_profile(
        session,
        telegram_id=db_user.telegram_id,
        user_id=db_user.id,
        work_formats=[fmt],
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(texts.profile_text(profile), reply_markup=profile_menu())
    await callback.answer(f"Формат: {fmt.value}")


@router.callback_query(F.data.startswith("profile:set:threshold:"))
async def set_threshold(callback: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    raw = (callback.data or "").rsplit(":", 1)[-1]
    try:
        threshold = int(raw)
    except ValueError:
        await callback.answer("Некорректный порог", show_alert=True)
        return
    if not 0 <= threshold <= 100:
        await callback.answer("Порог должен быть от 0 до 100", show_alert=True)
        return
    profile = await services.update_profile(
        session,
        telegram_id=db_user.telegram_id,
        user_id=db_user.id,
        min_match_score=threshold,
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            texts.settings_text(profile), reply_markup=settings_menu(profile)
        )
    await callback.answer(f"Порог: {threshold}%")


@router.callback_query(F.data == "profile:toggle_notifications")
async def toggle_notifications(
    callback: CallbackQuery, session: AsyncSession, db_user: User
) -> None:
    profile = await services.ensure_profile(session, db_user.telegram_id)
    updated: UserProfile = await services.update_profile(
        session,
        telegram_id=db_user.telegram_id,
        user_id=db_user.id,
        notifications_enabled=not profile.notifications_enabled,
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            texts.settings_text(updated), reply_markup=settings_menu(updated)
        )
    await callback.answer(
        "Уведомления включены" if updated.notifications_enabled else "Уведомления выключены"
    )


@router.callback_query(F.data == "menu:settings_back")
async def back_to_settings(callback: CallbackQuery) -> None:
    if isinstance(callback.message, Message):
        await callback.message.edit_text("Настройки", reply_markup=main_menu())
    await callback.answer()
