from app.tools.currency import convert_currency
from app.tools.places import search_places
from app.tools.travel import estimate_travel
from app.tools.weather import get_weather_forecast

ALL_TOOLS = [get_weather_forecast, search_places, estimate_travel, convert_currency]
