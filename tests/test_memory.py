import asyncio
from datetime import datetime, timezone

from langgraph.store.memory import InMemoryStore

from app.core.memory import (
    delete_profile,
    format_profile,
    merge_unique,
    read_profile,
    update_history,
    write_preferences,
)
from app.core.progress import emit_progress


def test_merge_unique_dedupes_and_keeps_recent():
    assert merge_unique(["Food", "forts"], ["food", "beaches"], 2) == [
        "forts",
        "beaches",
    ]


def test_update_history_caps_trips_and_puts_newest_first():
    history: dict = {}
    for i in range(7):
        history = update_history(
            history,
            cities=[f"City{i}"],
            days=3,
            budget=None,
            currency="INR",
            interests=["food"],
            feedback=[],
            now=datetime(2026, 11, 1, tzinfo=timezone.utc),
        )
    assert len(history["trips"]) == 5
    assert history["trips"][0]["cities"] == ["City6"]
    assert history["interests"] == ["food"]


def test_format_profile():
    assert format_profile(None) == "No saved preferences."
    text = format_profile(
        {"explicit": {"diet": "vegetarian", "pace": "relaxed"}, "learned": {}}
    )
    assert "vegetarian" in text and "relaxed" in text


def test_store_roundtrip_and_delete():
    async def scenario():
        store = InMemoryStore()
        await write_preferences(store, "u1", {"diet": "vegetarian"})
        profile = await read_profile(store, "u1")
        assert profile["explicit"]["diet"] == "vegetarian"
        assert profile["learned"] == {}
        await delete_profile(store, "u1")
        assert (await read_profile(store, "u1"))["explicit"] == {}
        assert (await read_profile(None, "u1")) == {"explicit": {}, "learned": {}}
        assert (await read_profile(store, "anonymous")) == {
            "explicit": {},
            "learned": {},
        }

    asyncio.run(scenario())


def test_emit_progress_outside_graph_is_a_noop():
    emit_progress("test", "no graph is running")  # must not raise
