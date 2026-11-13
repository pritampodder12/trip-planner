import logging
from math import asin, cos, radians, sin, sqrt

import httpx
from langchain_core.tools import tool

from app.tools.geo import geocode

logger = logging.getLogger(__name__)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    return 6371 * 2 * asin(sqrt(a))


@tool
async def estimate_travel(origin_city: str, destination_city: str) -> str:
    """Roughly estimate the road distance and driving time between two cities.
    This is an approximation from coordinates, not a live route or a train/flight
    timetable."""
    # logger.info("[tool] estimate_travel | origin=%r destination=%r", origin_city, destination_city)
    try:
        a = await geocode(origin_city)
        b = await geocode(destination_city)
    except httpx.HTTPError as e:
        return f"Geocoding error: {e}"
    if a is None or b is None:
        return "Could not find one of the cities."
    straight = _haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
    road = straight * 1.3  # roads are rarely straight
    hours = road / 50  # assumed average speed of 50 km/h
    return (
        f"{a['name']} to {b['name']}: about {straight:.0f} km straight-line, "
        f"about {road:.0f} km by road, roughly {hours:.1f} hours by car (estimate only)."
    )
