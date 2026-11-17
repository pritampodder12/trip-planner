# In-memory only — resets when bot restarts (fine for now; swap for SQLite in Phase 7)

_sessions: dict[int, str] = {}  # chat_id → thread_id


def get_thread(chat_id: int) -> str | None:
    return _sessions.get(chat_id)


def set_thread(chat_id: int, thread_id: str) -> None:
    _sessions[chat_id] = thread_id


def clear_thread(chat_id: int) -> None:
    _sessions.pop(chat_id, None)


def has_thread(chat_id: int) -> bool:
    return chat_id in _sessions
