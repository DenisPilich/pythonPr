"""Pure text builders for the bot.

Keeping rendering out of handlers makes every message snapshot-testable and keeps
HTML escaping in one place.
"""

from __future__ import annotations

from html import escape

from app.models import AIAnalysis, UserProfile, UserVacancy, Vacancy
from app.schemas.stats import StatsResponse
from app.services.notification_format import format_salary


def start_text(first_name: str | None) -> str:
    name = f", {escape(first_name)}" if first_name else ""
    return (
        f"👋 Привет{name}!\n\n"
        "Я <b>AI Job Radar</b> — слежу за вакансиями разработчиков, сравниваю их "
        "с твоим профилем и присылаю только подходящие.\n\n"
        "1. Заполни профиль\n"
        "2. Настрой фильтры и порог совпадения\n"
        "3. Получай уведомления в этот чат\n\n"
        "Команды: /profile /jobs /top /stats /settings /help"
    )


def help_text() -> str:
    return (
        "<b>Команды</b>\n\n"
        "/start — начать\n"
        "/profile — профиль и его редактирование\n"
        "/jobs — последние найденные вакансии\n"
        "/top — лучшие совпадения\n"
        "/stats — статистика\n"
        "/settings — уведомления и порог\n"
        "/help — эта справка\n\n"
        "В уведомлении можно открыть вакансию, сохранить её, отметить "
        "«Applied» или скрыть."
    )


def profile_missing_text() -> str:
    return (
        "Профиль ещё не создан.\n\n"
        "Создай его и заполни навыки, стек, уровень и зарплатные ожидания — "
        "тогда AI сможет сравнивать вакансии именно с тобой."
    )


def _value(value: str | None) -> str:
    return escape(value) if value else "—"


def _list(values: list[str]) -> str:
    return ", ".join(escape(item) for item in values) if values else "—"


def profile_text(profile: UserProfile) -> str:
    salary = (
        f"от {profile.min_salary_amount} {profile.salary_currency}"
        if profile.min_salary_amount
        else "—"
    )
    formats = ", ".join(fmt.value for fmt in profile.work_formats) or "—"
    levels = ", ".join(level.value for level in profile.target_seniority) or "—"
    return "\n".join(
        [
            "👤 <b>Твой профиль</b>",
            "",
            f"О себе: {_value(profile.headline)}",
            f"Позиции: {_list(profile.desired_positions)}",
            f"Уровень: {escape(levels)}",
            f"Навыки: {_list(profile.skills)}",
            f"Стек: {_list(profile.preferred_stack)}",
            f"Английский: {profile.english_level.value.upper()}",
            f"Зарплата: {escape(salary)}",
            f"Локации: {_list(profile.preferred_locations)}",
            f"Формат: {escape(formats)}",
            "",
            f"Порог уведомлений: <b>{profile.min_match_score}%</b>",
            f"Уведомления: {'включены' if profile.notifications_enabled else 'выключены'}",
        ]
    )


def settings_text(profile: UserProfile) -> str:
    return (
        "⚙️ <b>Настройки</b>\n\n"
        f"Уведомления: {'включены' if profile.notifications_enabled else 'выключены'}\n"
        f"Порог совпадения: {profile.min_match_score}%\n"
        f"Лимит в день: {profile.max_notifications_per_day}\n\n"
        "Порог — минимальный Match Score, при котором вакансия придёт в чат."
    )


def vacancy_card_text(
    vacancy: Vacancy,
    *,
    analysis: AIAnalysis | None,
    status: UserVacancy | None = None,
) -> str:
    score = analysis.match_score if analysis else (status.match_score if status else None)
    recommendation = analysis.recommendation.value.upper() if analysis else None
    salary = format_salary(
        minimum=vacancy.salary_min,
        maximum=vacancy.salary_max,
        currency=vacancy.salary_currency,
        period=vacancy.salary_period,
        monthly_eur=vacancy.salary_monthly_eur,
    )
    lines = [
        f"<b>{escape(vacancy.title)}</b>",
        f"{escape(vacancy.company.name)} · {vacancy.work_format.value} · {vacancy.seniority.value}",
        f"{escape(salary)}",
    ]
    if score is not None:
        suffix = f" · {recommendation}" if recommendation else ""
        lines.append(f"🎯 <b>{score}%</b>{suffix}")
    if status is not None:
        lines.append(f"Статус: {status.status.value}")
    return "\n".join(lines)


def stats_text(stats: StatsResponse, personal: dict[str, int]) -> str:
    top = ", ".join(f"{item.name} ({item.count})" for item in stats.top_technologies[:5])
    return (
        "📊 <b>Статистика</b>\n\n"
        f"Всего вакансий: <b>{stats.vacancies.total}</b>\n"
        f"Новых за 7 дней: {stats.vacancies.new_last_7_days}\n"
        f"С зарплатой: {stats.vacancies.with_salary}\n"
        f"Remote: {stats.vacancies.remote_share:.0%}\n\n"
        f"Топ технологий: {escape(top or '—')}\n\n"
        "<b>Твоя история</b>\n"
        f"Отправлено: {personal.get('sent', 0)}\n"
        f"Просмотрено: {personal.get('viewed', 0)}\n"
        f"Сохранено: {personal.get('saved', 0)}\n"
        f"Applied: {personal.get('applied', 0)}\n"
        f"Скрыто: {personal.get('rejected', 0)}"
    )
