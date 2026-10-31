from functools import lru_cache

from langchain_core.prompts import ChatPromptTemplate

from app.core.llm import get_llm
from app.graph.state import TripState
from app.schemas.plan import CityPlan

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a travel route planner. Split the total trip days across the "
            "cities and order them to minimise travel time. Every city gets at least "
            "1 day, and the days must add up exactly to the total trip days.",
        ),
        ("human", "trip request:\n{request_json}"),
    ]
)


@lru_cache
def get_chain():
    return prompt | get_llm().with_structured_output(CityPlan)


async def city_allocator_node(state: TripState) -> dict:
    plan = await get_chain().ainvoke(
        {"request_json": state["request"].model_dump_json()}
    )
    return {"city_plan": plan}
