"""Profile persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserProfile


class ProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user(self, telegram_id: int) -> User | None:
        return await self._session.scalar(select(User).where(User.telegram_id == telegram_id))

    async def get_profile(self, telegram_id: int) -> UserProfile | None:
        return await self._session.scalar(
            select(UserProfile)
            .join(User, User.id == UserProfile.user_id)
            .where(User.telegram_id == telegram_id)
        )

    async def create_user(self, telegram_id: int) -> User:
        user = User(telegram_id=telegram_id)
        self._session.add(user)
        await self._session.flush()
        return user

    async def add_profile(self, profile: UserProfile) -> UserProfile:
        self._session.add(profile)
        await self._session.flush()
        return profile
