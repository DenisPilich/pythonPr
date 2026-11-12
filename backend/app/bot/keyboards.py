"""Inline keyboards and callback-data conventions.

Callback data is a plain colon-separated string; parsers validate every segment
before using it, so a malformed callback cannot reach the database.
"""

from __future__ import annotations

import uuid

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.domain.enums import SeniorityLevel, WorkFormat
from app.models import UserProfile


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👤 Профиль", callback_data="menu:profile"),
                InlineKeyboardButton(text="💼 Вакансии", callback_data="menu:jobs"),
            ],
            [
                InlineKeyboardButton(text="🏆 Топ", callback_data="menu:top"),
                InlineKeyboardButton(text="📊 Статистика", callback_data="menu:stats"),
            ],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings")],
        ]
    )


def back_to_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ В меню", callback_data="menu:main")]]
    )


def create_profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Создать профиль", callback_data="profile:create")],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu:main")],
        ]
    )


def profile_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Навыки", callback_data="profile:edit:skills"),
                InlineKeyboardButton(text="Стек", callback_data="profile:edit:stack"),
            ],
            [
                InlineKeyboardButton(text="Зарплата", callback_data="profile:edit:salary"),
                InlineKeyboardButton(text="Уровень", callback_data="profile:edit:seniority"),
            ],
            [
                InlineKeyboardButton(text="Формат", callback_data="profile:edit:format"),
                InlineKeyboardButton(text="Порог", callback_data="profile:edit:threshold"),
            ],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu:main")],
        ]
    )


def settings_menu(profile: UserProfile) -> InlineKeyboardMarkup:
    toggle = "🔕 Выключить" if profile.notifications_enabled else "🔔 Включить"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=toggle, callback_data="profile:toggle_notifications")],
            [
                InlineKeyboardButton(text="Порог 50%", callback_data="profile:set:threshold:50"),
                InlineKeyboardButton(text="Порог 70%", callback_data="profile:set:threshold:70"),
                InlineKeyboardButton(text="Порог 80%", callback_data="profile:set:threshold:80"),
            ],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu:main")],
        ]
    )


def seniority_menu() -> InlineKeyboardMarkup:
    levels = (SeniorityLevel.JUNIOR, SeniorityLevel.MIDDLE, SeniorityLevel.SENIOR)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=level.value.title(),
                    callback_data=f"profile:set:seniority:{level.value}",
                )
                for level in levels
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:profile")],
        ]
    )


def format_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=fmt.value.title(), callback_data=f"profile:set:format:{fmt.value}"
                )
                for fmt in (WorkFormat.REMOTE, WorkFormat.HYBRID, WorkFormat.OFFICE)
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:profile")],
        ]
    )


def threshold_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="50%", callback_data="profile:set:threshold:50"),
                InlineKeyboardButton(text="70%", callback_data="profile:set:threshold:70"),
                InlineKeyboardButton(text="80%", callback_data="profile:set:threshold:80"),
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:profile")],
        ]
    )


def cancel_edit() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="menu:profile")]]
    )


def vacancy_actions(vacancy_id: uuid.UUID, url: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if url:
        rows.append([InlineKeyboardButton(text="🔗 Открыть вакансию", url=url)])
    rows.append(
        [
            InlineKeyboardButton(text="💾 Сохранить", callback_data=f"vac:save:{vacancy_id}"),
            InlineKeyboardButton(text="✅ Applied", callback_data=f"vac:applied:{vacancy_id}"),
            InlineKeyboardButton(text="🚫 Skip", callback_data=f"vac:skip:{vacancy_id}"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
