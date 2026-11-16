import logging

from langgraph.runtime import Runtime

from app.core.logging_config import log_call
from app.core.memory import (
    ANONYMOUS_USER,
    read_profile,
    update_history,
    write_history,
)
from app.graph.state import TripState

logger = logging.getLogger(__name__)


@log_call("node")
async def load_preferences_node(state: TripState, runtime: Runtime) -> dict:
    user_id = state.get("user_id", ANONYMOUS_USER)
    if runtime.store is None:
        logger.warning("No store configured; continuing without preferences")
    profile = await read_profile(runtime.store, user_id)
    logger.info(
        "Loaded preferences for user_id=%s: explicit_keys=%s learned_keys=%s",
        user_id,
        list(profile["explicit"]),
        list(profile["learned"]),
    )
    return {"preferences": profile}


@log_call("node")
async def save_preferences_node(state: TripState, runtime: Runtime) -> dict:
    user_id = state.get("user_id", ANONYMOUS_USER)
    if not state.get("approved"):
        logger.info("Not saving history: the itinerary was not approved")
        return {}
    if user_id == ANONYMOUS_USER or runtime.store is None:
        logger.info("Not saving history (anonymous user or no store)")
        return {}

    req = state["request"]
    profile = await read_profile(runtime.store, user_id)
    updated = update_history(
        profile["learned"],
        cities=req.cities,
        days=req.days,
        budget=req.budget,
        currency=req.currency,
        interests=req.interests,
        feedback=state.get("feedback_log", []),
    )
    await write_history(runtime.store, user_id, updated)
    logger.info(
        "Saved history for user_id=%s: %d interest(s), %d trip(s)",
        user_id,
        len(updated["interests"]),
        len(updated["trips"]),
    )
    return {}
