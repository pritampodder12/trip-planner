import logging
from collections import defaultdict
from datetime import date, datetime, timedelta

import httpx
from langchain_core.tools import tool

from app.core.config import settings
from app.core.logging_config import log_call
from app.tools.geo import geocode, get_json

logger = logging.getLogger(__name__)


async def _open_meteo(place: dict, days: int) -> str:
    data = await get_json(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": place["lat"],
            "longitude": place["lon"],
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "auto",
            "forecast_days": days,
        },
    )
    d = data["daily"]
    return "\n".join(
        f"{d['time'][i]}: {d['temperature_2m_min'][i]} to {d['temperature_2m_max'][i]}°C, "
        f"rain chance {d['precipitation_probability_max'][i]}%"
        for i in range(len(d["time"]))
    )


async def _met_norway(place: dict, days: int) -> str:
    data = await get_json(
        "https://api.met.no/weatherapi/locationforecast/2.0/compact",
        {"lat": round(place["lat"], 4), "lon": round(place["lon"], 4)},
    )
    temps: dict[str, list[float]] = defaultdict(list)
    rain: dict[str, float] = defaultdict(float)
    for slot in data["properties"]["timeseries"]:
        t = datetime.fromisoformat(slot["time"].replace("Z", "+00:00"))
        day = t.date().isoformat()  # UTC day, so edges can be off by a few hours
        payload = slot["data"]
        temps[day].append(payload["instant"]["details"]["air_temperature"])
        if "next_1_hours" in payload:
            rain[day] += (
                payload["next_1_hours"]
                .get("details", {})
                .get("precipitation_amount", 0)
            )
        elif "next_6_hours" in payload and t.hour % 6 == 0:  # later slots are 6-hourly
            rain[day] += (
                payload["next_6_hours"]
                .get("details", {})
                .get("precipitation_amount", 0)
            )
    return "\n".join(
        f"{day}: {min(temps[day]):.0f} to {max(temps[day]):.0f}°C, expected rain {rain[day]:.1f} mm"
        for day in sorted(temps)[:days]
    )


def _mock(city: str, days: int) -> str:
    today = date.today()
    lines = [
        f"{(today + timedelta(days=i)).isoformat()}: 19 to 31°C, rain chance 10%"
        for i in range(days)
    ]
    return f"[MOCK DATA, not a real forecast] Forecast for {city}:\n" + "\n".join(lines)


@tool
@log_call("tool", log_args=True)
async def get_weather_forecast(city: str, days: int = 5) -> str:
    """Get the daily weather forecast for a city: min/max temperature in °C and
    rain. Only covers about the next 10 days; for trips further away, tell the
    user that exact weather is not known yet."""
    # logger.info("[tool] get_weather_forecast | city=%r days=%d", city, days)
    days = max(1, min(days, 10))

    # if settings.weather_mock:
    #     return _mock(city, days)

    try:
        place = await geocode(city)
    except httpx.HTTPError as e:
        return f"Could not look up '{city}' ({type(e).__name__}). Do not guess the weather."
    if place is None:
        return f"Could not find a city named '{city}'."

    errors = []
    for name, fetch in (("Open-Meteo", _open_meteo), ("MET Norway", _met_norway)):
        try:
            body = await fetch(place, days)
            return f"Forecast for {place['name']}, {place['country']} (source: {name}):\n{body}"
        except (httpx.HTTPError, KeyError, ValueError) as e:
            errors.append(f"{name}: {type(e).__name__}")

    return "Weather unavailable (" + "; ".join(errors) + "). Do not guess the weather."
