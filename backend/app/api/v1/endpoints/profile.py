"""`/profile` — the user's matching profile (one per Telegram account)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import SessionDep, TelegramIdDep, require_api_key
from app.api.v1.mappers import profile_to_read
from app.models import UserProfile
from app.schemas.profile import ProfilePayload, ProfileRead
from app.services.profile import ProfileService


router = APIRouter(prefix="/profile", tags=["profile"])


def _read(profile: UserProfile, telegram_id: int) -> ProfileRead:
    return profile_to_read(profile, telegram_id)


@router.get(
    "",
    response_model=ProfileRead,
    summary="Read the current profile",
    description=(
        "Resolves the profile by `X-Telegram-Id` header. Without the header the "
        "demo user from configuration is used."
    ),
    responses={404: {"description": "Profile not created yet"}},
)
async def get_profile(session: SessionDep, telegram_id: TelegramIdDep) -> ProfileRead:
    profile = await ProfileService(session).get(telegram_id)
    return _read(profile, telegram_id)


@router.post(
    "",
    response_model=ProfileRead,
    status_code=201,
    summary="Create a profile",
    description="Requires `X-API-Key`. Fails with 409 when the profile already exists.",
    dependencies=[Depends(require_api_key)],
    responses={409: {"description": "Profile already exists"}},
)
async def create_profile(
    payload: ProfilePayload, session: SessionDep, telegram_id: TelegramIdDep
) -> ProfileRead:
    profile = await ProfileService(session).create(telegram_id, payload)
    return _read(profile, telegram_id)


@router.put(
    "",
    response_model=ProfileRead,
    summary="Replace a profile",
    description=(
        "Requires `X-API-Key`. Full replacement; creates the profile when it does not "
        "exist yet, so the bot and the dashboard can use one call."
    ),
    dependencies=[Depends(require_api_key)],
)
async def upsert_profile(
    payload: ProfilePayload, session: SessionDep, telegram_id: TelegramIdDep
) -> ProfileRead:
    profile = await ProfileService(session).upsert(telegram_id, payload)
    return _read(profile, telegram_id)
