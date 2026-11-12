"""`/jobs` and `/top`: the user's matched vacancies with inline actions."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, LinkPreviewOptions, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import services, texts
from app.bot.keyboards import main_menu, vacancy_actions
from app.models import User


router = Router(name="jobs")


def _url_for(vacancy: object) -> str:
    references = sorted(getattr(vacancy, "sources", []), key=lambda ref: ref.first_seen_at)
    return references[0].url if references else ""


async def _send_cards(
    message: Message,
    session: AsyncSession,
    db_user: User,
    *,
    by_score: bool,
    empty_text: str,
) -> None:
    rows = await services.list_user_vacancies(session, db_user.id, limit=5, by_score=by_score)
    if not rows:
        await message.answer(empty_text, reply_markup=main_menu())
        return
    for tracked, vacancy, analysis in rows:
        await message.answer(
            texts.vacancy_card_text(vacancy, analysis=analysis, status=tracked),
            reply_markup=vacancy_actions(vacancy.id, _url_for(vacancy)),
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )


@router.message(Command("jobs"))
async def cmd_jobs(message: Message, session: AsyncSession, db_user: User) -> None:
    await _send_cards(
        message,
        session,
        db_user,
        by_score=False,
        empty_text="Пока нет вакансий. Заполни профиль — и я начну присылать подходящие.",
    )


@router.message(Command("top"))
async def cmd_top(message: Message, session: AsyncSession, db_user: User) -> None:
    await _send_cards(
        message,
        session,
        db_user,
        by_score=True,
        empty_text="Пока нет оценённых вакансий. Проверь позже.",
    )


@router.callback_query(F.data == "menu:jobs")
async def menu_jobs(callback: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    if isinstance(callback.message, Message):
        await _send_cards(
            callback.message,
            session,
            db_user,
            by_score=False,
            empty_text="Пока нет вакансий. Заполни профиль — и я начну присылать подходящие.",
        )
    await callback.answer()


@router.callback_query(F.data == "menu:top")
async def menu_top(callback: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    if isinstance(callback.message, Message):
        await _send_cards(
            callback.message,
            session,
            db_user,
            by_score=True,
            empty_text="Пока нет оценённых вакансий. Проверь позже.",
        )
    await callback.answer()
