import os

import httpx

API_URL = os.environ.get("TRIP_API_URL", "http://localhost:8000")

# Timeout is 120s because LLM calls can take 60–90s
_TIMEOUT = httpx.Timeout(120.0)


async def create_trip(text: str, user_id: str) -> dict:
    """POST /trips — starts a brand new trip."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as http:
        r = await http.post(
            f"{API_URL}/trips",
            json={"text": text, "user_id": user_id},
        )
        r.raise_for_status()
        return r.json()


async def resume_trip(thread_id: str, answer: str) -> dict:
    """POST /trips/{id}/resume — answers a clarification question."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as http:
        r = await http.post(
            f"{API_URL}/trips/{thread_id}/resume",
            json={"answer": answer},
        )
        r.raise_for_status()
        return r.json()


async def approve_trip(
    thread_id: str,
    approved: bool,
    feedback: str | None = None,
) -> dict:
    """POST /trips/{id}/resume — approves or requests changes."""
    body: dict = {"approved": approved}
    if feedback:
        body["feedback"] = feedback
    async with httpx.AsyncClient(timeout=_TIMEOUT) as http:
        r = await http.post(
            f"{API_URL}/trips/{thread_id}/resume",
            json=body,
        )
        r.raise_for_status()
        return r.json()
