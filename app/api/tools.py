from fastapi import APIRouter

from app.tools.weather import get_weather_forecast

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/weather")
async def weather(city: str, days: int = 3):
    return {"result": await get_weather_forecast.ainvoke({"city": city, "days": days})}
