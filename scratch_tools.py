import asyncio

from app.tools import ALL_TOOLS


async def main():
    by_name = {t.name: t for t in ALL_TOOLS}
    print(await by_name["get_weather_forecast"].ainvoke({"city": "Jaipur", "days": 3}))
    print(
        await by_name["search_places"].ainvoke({"city": "Jaipur", "interest": "forts"})
    )
    print(
        await by_name["estimate_travel"].ainvoke(
            {"origin_city": "Jaipur", "destination_city": "Udaipur"}
        )
    )
    print(
        await by_name["convert_currency"].ainvoke(
            {"amount": 500, "from_currency": "USD", "to_currency": "INR"}
        )
    )
    print(
        await by_name["get_weather_forecast"].ainvoke({"city": "Atlantisville"})
    )  # error path


asyncio.run(main())
