import asyncio

import httpx

RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# Wikimedia asks every client to send a descriptive User-Agent
HEADERS = {
    "User-Agent": "TripPlannerLearning/0.1 (https://github.com/pritampodder12/trip-planner; pritampodder12@gmail.com)"
}


async def get_json(url: str, params: dict, retries: int = 2) -> dict:
    """GET with a short retry for temporary failures (timeouts, 5xx, 429)."""
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=10, headers=HEADERS) as client:
                r = await client.get(url, params=params)
            if r.status_code in RETRYABLE_STATUS and attempt < retries:
                await asyncio.sleep(1.5 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()
        except httpx.TransportError:  # includes timeouts and connection errors
            if attempt == retries:
                raise
            await asyncio.sleep(1.5 * (attempt + 1))


_cache: dict[str, dict] = {}


async def geocode(city: str) -> dict | None:
    key = city.strip().lower()
    if key in _cache:
        return _cache[key]
    data = await get_json(
        "https://geocoding-api.open-meteo.com/v1/search", {"name": city, "count": 1}
    )
    results = data.get("results")
    if not results:
        return None
    top = results[0]
    place = {
        "name": top["name"],
        "country": top.get("country", ""),
        "lat": top["latitude"],
        "lon": top["longitude"],
    }
    _cache[key] = place
    return place
