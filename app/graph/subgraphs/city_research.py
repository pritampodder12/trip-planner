import logging
import re
from functools import lru_cache
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from app.core.llm import get_llm
from app.core.logging_config import log_call
from app.core.progress import emit_progress
from app.graph.state import CityNotes, merge_dicts
from app.schemas.trip import TripRequest
from app.tools.places import search_places
from app.tools.travel import estimate_travel
from app.tools.weather import get_weather_forecast

logger = logging.getLogger(__name__)

CITY_TOOLS = [get_weather_forecast, search_places, estimate_travel]

SYSTEM_PROMPT = (
    "You research ONE city for a trip. Tools:\n"
    "- get_weather_forecast(city, days): call once.\n"
    "- search_places(city, interest): once per traveler interest (at most 3; if no "
    "interests are given use 'tourist attractions' and 'restaurants').\n"
    "- estimate_travel(origin, destination): only if a previous city is given.\n"
    "Request ALL independent tool calls together in the same step, not one by one.\n"
    "Respect the traveler profile (diet, dislikes, pace) when choosing what to search for.\n"
    "Never invent places or numbers. If a tool fails, say so. Make at most 6 tool calls.\n"
    "Then stop calling tools and write concise notes: weather, 5-8 recommended places "
    "grouped by interest (only names from tool results), practical tips, and travel "
    "time from the previous city if known."
)


class CityTask(TypedDict):
    """Input: what the parent sends with Send(...)."""

    city: str
    days: int
    previous_city: str | None
    profile: str
    request: TripRequest


class CityOutput(TypedDict):
    """Output: the ONLY key handed back to the parent graph."""

    city_notes: Annotated[dict[str, CityNotes], merge_dicts]


class CityResearchState(CityTask, CityOutput):
    """Full internal state of the subgraph."""

    messages: Annotated[list[AnyMessage], add_messages]


def _message_text(msg) -> str:
    content = msg.content
    if isinstance(content, str):
        return content
    return "".join(
        b.get("text", "")
        for b in content
        if isinstance(b, dict) and b.get("type") == "text"
    )


@lru_cache
def _agent_llm():
    return get_llm().bind_tools(CITY_TOOLS)


@log_call("node")
def city_prepare_node(state: CityResearchState) -> dict:
    city, req = state["city"], state["request"]
    logger.info("Subgraph research started for city=%s days=%s", city, state["days"])
    emit_progress("research", f"Researching {city}", city=city)
    prompt = (
        f"City: {city}\n"
        f"Days in this city: {state['days']}\n"
        f"Previous city: {state['previous_city'] or 'none (trip starts here)'}\n"
        f"Traveler interests: {', '.join(req.interests) or 'not specified'}\n"
        f"Traveler profile: {state['profile']}\n"
        f"Travelers: {req.travelers}, budget: {req.budget} {req.currency}"
    )
    return {"messages": [HumanMessage(content=prompt)]}


@log_call("node")
async def city_agent_node(state: CityResearchState) -> dict:
    response = await _agent_llm().ainvoke(
        [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
    )
    calls = [c["name"] for c in (getattr(response, "tool_calls", None) or [])]
    logger.info(
        "City agent (%s) requested tools: %s",
        state["city"],
        calls or "none (finishing)",
    )
    return {"messages": [response]}


@log_call("node")
def city_finalize_node(state: CityResearchState) -> dict:
    city, messages = state["city"], state["messages"]
    places: list[str] = []
    for m in messages:
        if isinstance(m, ToolMessage) and m.name == "search_places":
            places += re.findall(r"^- (.+?):", str(m.content), flags=re.MULTILINE)
    places = list(dict.fromkeys(places))  # de-duplicate, keep order
    note: CityNotes = {
        "city": city,
        "notes": _message_text(messages[-1]),
        "places": places,
    }
    logger.info(
        "Subgraph research finished for city=%s: %d place(s)", city, len(places)
    )
    emit_progress(
        "research", f"Finished {city}: {len(places)} place(s) found", city=city
    )
    return {"city_notes": {city: note}}


def build_city_research_graph():
    graph = StateGraph(
        CityResearchState, input_schema=CityTask, output_schema=CityOutput
    )
    graph.add_node("prepare", city_prepare_node)
    graph.add_node("agent", city_agent_node)
    graph.add_node("tools", ToolNode(CITY_TOOLS))
    graph.add_node("finalize", city_finalize_node)
    graph.add_edge(START, "prepare")
    graph.add_edge("prepare", "agent")
    graph.add_conditional_edges(
        "agent", tools_condition, {"tools": "tools", END: "finalize"}
    )
    graph.add_edge("tools", "agent")
    graph.add_edge("finalize", END)
    return graph.compile()  # no checkpointer: inherits the parent's
