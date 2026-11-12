"""FSM states for the profile editor."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class ProfileEdit(StatesGroup):
    skills = State()
    stack = State()
    salary = State()
