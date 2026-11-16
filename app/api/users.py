import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Request

from app.core.memory import (
    ANONYMOUS_USER,
    delete_profile,
    read_profile,
    write_preferences,
)
from app.schemas.preferences import PreferencesIn, PreferencesOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])

UserId = Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{1,64}$")]


def _check(user_id: str) -> None:
    if user_id == ANONYMOUS_USER:
        raise HTTPException(
            status_code=400, detail="Preferences are not stored for the anonymous user."
        )


@router.get("/{user_id}/preferences", response_model=PreferencesOut)
async def get_preferences(user_id: UserId, request: Request) -> PreferencesOut:
    logger.info("GET /users/%s/preferences", user_id)
    _check(user_id)
    profile = await read_profile(request.app.state.store, user_id)
    return PreferencesOut(
        user_id=user_id, preferences=profile["explicit"], history=profile["learned"]
    )


@router.put("/{user_id}/preferences", response_model=PreferencesOut)
async def put_preferences(
    user_id: UserId, body: PreferencesIn, request: Request
) -> PreferencesOut:
    logger.info(
        "PUT /users/%s/preferences: %s", user_id, body.model_dump(exclude_none=True)
    )
    _check(user_id)
    store = request.app.state.store
    await write_preferences(store, user_id, body.model_dump())
    profile = await read_profile(store, user_id)
    return PreferencesOut(
        user_id=user_id, preferences=profile["explicit"], history=profile["learned"]
    )


@router.delete("/{user_id}/preferences", status_code=204)
async def remove_preferences(user_id: UserId, request: Request) -> None:
    logger.info("DELETE /users/%s/preferences", user_id)
    _check(user_id)
    await delete_profile(request.app.state.store, user_id)
