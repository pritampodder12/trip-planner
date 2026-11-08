import logging
import re
from functools import lru_cache
from typing import TypedDict

from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Send

from app.graph.state import TripState
from app.graph.subgraphs.city_research import build_city_research_graph
from app.schemas.trip import TripRequest

logger = logging.getLogger(__name__)


class CityTask(TypedDict):
    """The private input each parallel branch receives."""

    city: str
    days: int
    previous_city: str | None
    request: TripRequest


@lru_cache
def get_city_graph():
    return build_city_research_graph()


def message_text(msg) -> str:
    content = msg.content
    if isinstance(content, str):
        return content
    return "".join(
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    )


def fan_out_research(state: TripState) -> list[Send]:
    """Conditional edge that returns one Send per city (map step)."""
    stays = state["city_plan"].stays
    return [
        Send(
            "research_city",
            {
                "city": stay.city,
                "days": stay.days,
                "previous_city": stays[i - 1].city if i > 0 else None,
                "request": state["request"],
            },
        )
        for i, stay in enumerate(stays)
    ]


async def research_city_node(task: CityTask, config: RunnableConfig) -> dict:
    req = task["request"]
    prompt = (
        f"City: {task['city']}\n"
        f"Days in this city: {task['days']}\n"
        f"Previous city: {task['previous_city'] or 'none (trip starts here)'}\n"
        f"Traveler interests: {', '.join(req.interests) or 'not specified'}\n"
        f"Travelers: {req.travelers}, budget: {req.budget} {req.currency}"
    )
    # Pass `config` so callbacks (token logging, tracing) also see the nested calls.
    result = await get_city_graph().ainvoke(
        {"messages": [HumanMessage(content=prompt)]}, config=config
    )
    messages = result["messages"]
    places: list[str] = []
    for m in messages:
        if isinstance(m, ToolMessage) and m.name == "search_places":
            places += re.findall(r"^- (.+?):", str(m.content), flags=re.MULTILINE)

    note = {"city": task["city"], "notes": message_text(messages[-1]), "places": places}
    return {"city_notes": {task["city"]: note}}  # merged by merge_dicts
