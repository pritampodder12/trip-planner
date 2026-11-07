import logging

import httpx
from langchain_core.tools import tool

from app.tools.geo import get_json

logger = logging.getLogger(__name__)


@tool
async def search_places(city: str, interest: str) -> str:
    """Find places in a city that match one interest, for example city='Jaipur',
    interest='forts'. Returns up to 6 place names with a short description.
    Call it once per city and interest."""
    logger.info("[tool] search_places | city=%r interest=%r", city, interest)
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"{interest} in {city}",
        "gsrlimit": 6,
        "prop": "extracts",
        "exintro": 1,
        "explaintext": 1,
        "exsentences": 2,
        "exlimit": 6,
    }
    try:
        data = await get_json("https://en.wikipedia.org/w/api.php", params)
        pages = data.get("query", {}).get("pages", {})
    except httpx.HTTPError as e:
        return f"Place search error for '{interest}' in {city}: {type(e).__name__}: {e}"

    if not pages:
        return f"No results for '{interest}' in {city}."
    ranked = sorted(pages.values(), key=lambda p: p.get("index", 99))
    lines = [f"- {p['title']}: {p.get('extract', '').strip()[:300]}" for p in ranked]
    return f"Places for '{interest}' in {city}:\n" + "\n".join(lines)
