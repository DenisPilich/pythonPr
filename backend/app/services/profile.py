"""Profile use cases: create, replace, read.

`profile_hash` is recomputed on every write and stored with the row; the AI layer
uses it as a cache key, so it must change exactly when a field that affects
matching changes.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.domain.profile import compute_profile_hash
from app.models import UserProfile
from app.repositories.profiles import ProfileRepository
from app.schemas.profile import ProfilePayload


class ProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = ProfileRepository(session)

    async def get(self, telegram_id: int) -> UserProfile:
        profile = await self._repository.get_profile(telegram_id)
        if profile is None:
            raise NotFoundError("Profile not found; create it with POST /api/v1/profile")
        return profile

    async def create(self, telegram_id: int, payload: ProfilePayload) -> UserProfile:
        if await self._repository.get_profile(telegram_id) is not None:
            raise ConflictError("Profile already exists; use PUT /api/v1/profile")

        user = await self._repository.get_user(telegram_id)
        if user is None:
            user = await self._repository.create_user(telegram_id)

        profile = self._build(user_id=user.id, payload=payload)
        return await self._repository.add_profile(profile)

    async def upsert(self, telegram_id: int, payload: ProfilePayload) -> UserProfile:
        profile = await self._repository.get_profile(telegram_id)
        if profile is None:
            return await self.create(telegram_id, payload)

        for field, value in payload.model_dump().items():
            setattr(profile, field, value)
        profile.profile_hash = self._hash(payload)
        await self._session.flush()
        await self._session.refresh(profile)
        return profile

    def _build(self, *, user_id: uuid.UUID, payload: ProfilePayload) -> UserProfile:
        return UserProfile(
            user_id=user_id,
            profile_hash=self._hash(payload),
            **payload.model_dump(),
        )

    @staticmethod
    def _hash(payload: ProfilePayload) -> str:
        return compute_profile_hash(payload.model_dump(mode="json"))
