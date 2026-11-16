from functools import lru_cache
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from app.core.llm import get_llm
from app.core.logging_config import log_call
from app.tools.places import search_places
from app.tools.travel import estimate_travel
from app.tools.weather import get_weather_forecast

CITY_TOOLS = [get_weather_forecast, search_places, estimate_travel]

SYSTEM_PROMPT = (
    "You research ONE city for a trip. Tools:\n"
    "- get_weather_forecast(city, days): call once.\n"
    "- search_places(city, interest): once per traveler interest (at most 3; if no "
    "interests are given use 'tourist attractions' and 'restaurants').\n"
    "- estimate_travel(origin, destination): only if a previous city is given.\n"
    "Request ALL independent tool calls together in the same step, not one by one.\n"
    "Never invent places or numbers. If a tool fails, say so. Make at most 6 tool calls.\n"
    "Then stop calling tools and write concise notes: weather, 5-8 recommended places "
    "grouped by interest (only names from tool results), practical tips, and travel "
    "time from the previous city if known."
)


class CityResearchState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]


@lru_cache
def _agent_llm():
    return get_llm().bind_tools(CITY_TOOLS)


@log_call("node")
async def agent_node(state: CityResearchState) -> dict:
    response = await _agent_llm().ainvoke(
        [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
    )
    return {"messages": [response]}


def build_city_research_graph():
    g = StateGraph(CityResearchState)
    g.add_node("agent", agent_node)
    g.add_node("tools", ToolNode(CITY_TOOLS))
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    g.add_edge("tools", "agent")
    return g.compile()
