from functools import lru_cache

from langchain_core.prompts import ChatPromptTemplate

from app.core.llm import get_llm
from app.graph.state import TripState
from app.schemas.trip import TripRequest

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You extract trip details from the user's message. "
            "Never invent values. If something is not stated, leave it empty "
            "and add its name to missing info.",
        ),
        ("human", "{user_text}"),
    ]
)


@lru_cache
def get_chain():
    return prompt | get_llm().with_structured_output(TripRequest)


async def parse_trip_request(user_text: str) -> TripRequest:
    return await get_chain().ainvoke({"user_text": user_text})


async def intake_node(state: TripState) -> dict:
    request = await parse_trip_request(state["user_text"])
    return {"request": request}
