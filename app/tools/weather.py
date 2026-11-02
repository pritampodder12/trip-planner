import httpx
from langchain_core.tools import tool

from app.tools.geo import geocode, get_json


@tool
async def get_weather_forecast(city: str, days: int = 5) -> str:
    """Get the daily weather forecast for a city: min/max temperature in °C and
    chance of rain. Only covers the next 14 days; for trips further away, tell
    the user that exact weather is not known yet."""
    days = max(1, min(days, 14))
    try:
        place = await geocode(city)
        if place is None:
            return f"Could not find a city named '{city}'."
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
        lines = [
            f"{d['time'][i]}: {d['temperature_2m_min'][i]} to {d['temperature_2m_max'][i]}°C, "
            f"rain chance {d['precipitation_probability_max'][i]}%"
            for i in range(len(d["time"]))
        ]
        return f"Forecast for {place['name']}, {place['country']}:\n" + "\n".join(lines)
    except httpx.HTTPError as e:
        return f"Weather service error for '{city}': {e}"
