from functools import lru_cache

from langchain_core.prompts import ChatPromptTemplate

from app.core.llm import get_llm
from app.graph.state import TripState
from app.schemas.plan import Itinerary

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a travel planner. Create a day-by-day itinerary that follows the "
            "city plan exactly (same order, same number of days per city). Match the "
            "traveler's interests and budget. Keep each time slot to one or two sentences.",
        ),
        ("human", "Trip request:\n{request_json}\n\nCity plan:\n{plan_json}"),
    ]
)


@lru_cache
def get_chain():
    return prompt | get_llm().with_structured_output(Itinerary)


async def itinerary_builder_node(state: TripState) -> dict:
    itinerary = await get_chain().ainvoke(
        {
            "request_json": state["request"].model_dump_json(),
            "plan_json": state["city_plan"].model_dump_json(),
        }
    )
    return {"itinerary": itinerary}
