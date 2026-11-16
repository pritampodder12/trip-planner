import logging
from datetime import datetime, timezone

from langgraph.store.base import BaseStore

logger = logging.getLogger(__name__)

ANONYMOUS_USER = "anonymous"  # never stored: it would mix different people together
PREFS_KEY = "preferences"  # explicit, set by the user
HISTORY_KEY = "history"  # learned from approved trips
MAX_INTERESTS = 15
MAX_TRIPS = 5
MAX_FEEDBACK = 5


def user_namespace(user_id: str) -> tuple[str, str]:
    return ("users", user_id)


def _empty() -> dict:
    return {"explicit": {}, "learned": {}}


async def read_profile(store: BaseStore | None, user_id: str) -> dict:
    if store is None or user_id == ANONYMOUS_USER:
        logger.debug(
            "read_profile skipped (store=%s, user_id=%s)", store is not None, user_id
        )
        return _empty()
    ns = user_namespace(user_id)
    prefs = await store.aget(ns, PREFS_KEY)
    history = await store.aget(ns, HISTORY_KEY)
    logger.info(
        "Store read for user_id=%s: explicit=%s learned=%s",
        user_id,
        prefs is not None,
        history is not None,
    )
    return {
        "explicit": prefs.value if prefs else {},
        "learned": history.value if history else {},
    }


async def write_preferences(store: BaseStore, user_id: str, prefs: dict) -> None:
    logger.info("Store write: explicit preferences for user_id=%s", user_id)
    await store.aput(user_namespace(user_id), PREFS_KEY, prefs)


async def write_history(store: BaseStore, user_id: str, history: dict) -> None:
    logger.info("Store write: learned history for user_id=%s", user_id)
    await store.aput(user_namespace(user_id), HISTORY_KEY, history)


async def delete_profile(store: BaseStore, user_id: str) -> None:
    logger.info("Store delete: all data for user_id=%s", user_id)
    ns = user_namespace(user_id)
    await store.adelete(ns, PREFS_KEY)
    await store.adelete(ns, HISTORY_KEY)


def merge_unique(existing: list[str], new: list[str], limit: int) -> list[str]:
    """Append new items, drop case-insensitive duplicates, keep the most recent `limit`."""
    seen: set[str] = set()
    merged: list[str] = []
    for item in [*existing, *new]:
        clean = item.strip()
        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            merged.append(clean)
    return merged[-limit:]


def update_history(
    history: dict,
    *,
    cities: list[str],
    days: int,
    budget: float | None,
    currency: str,
    interests: list[str],
    feedback: list[str],
    now: datetime | None = None,
) -> dict:
    """Pure function: previous learned history + an approved trip = new learned history."""
    now = now or datetime.now(timezone.utc)
    trip = {
        "cities": cities,
        "days": days,
        "budget": budget,
        "currency": currency,
        "approved_at": now.isoformat(timespec="seconds"),
    }
    return {
        "interests": merge_unique(
            history.get("interests", []), interests, MAX_INTERESTS
        ),
        "trips": ([trip] + history.get("trips", []))[:MAX_TRIPS],  # newest first
        "feedback": merge_unique(history.get("feedback", []), feedback, MAX_FEEDBACK),
    }


def format_profile(profile: dict | None) -> str:
    """One readable line for prompts."""
    if not profile:
        return "No saved preferences."
    explicit = profile.get("explicit") or {}
    learned = profile.get("learned") or {}
    parts: list[str] = []
    if explicit.get("diet"):
        parts.append(f"Diet: {explicit['diet']}")
    if explicit.get("pace"):
        parts.append(f"Preferred pace: {explicit['pace']}")
    if explicit.get("budget_style"):
        parts.append(f"Budget style: {explicit['budget_style']}")
    if explicit.get("dislikes"):
        parts.append("Dislikes: " + ", ".join(explicit["dislikes"]))
    if explicit.get("notes"):
        parts.append(f"Notes: {explicit['notes']}")
    if learned.get("interests"):
        parts.append("Interests from past trips: " + ", ".join(learned["interests"]))
    if learned.get("feedback"):
        parts.append("Changes they asked for before: " + "; ".join(learned["feedback"]))
    return "; ".join(parts) or "No saved preferences."
