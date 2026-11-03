from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import get_llm
from app.graph.state import TripState
from app.tools import ALL_TOOLS

SYSTEM_PROMPT = (
    "You are a travel research assistant. Use the tools to collect facts for the trip.\n"
    "Rules:\n"
    "- Call get_weather_forecast once per city.\n"
    "- Call search_places for each city, once per traveler interest (at most 2 interests per city).\n"
    "- Call estimate_travel between consecutive cities.\n"
    "- Call convert_currency only if the budget needs converting.\n"
    "- Never invent places or numbers. If a tool fails, say so in your notes.\n"
    "- Make at most 10 tool calls in total.\n"
    "When you have enough, stop calling tools and write concise research notes: "
    "weather per city, a shortlist of place names (only from tool results), "
    "travel between cities, and the budget."
)


@lru_cache
def get_agent_llm():
    return get_llm().bind_tools(ALL_TOOLS)


def message_text(msg) -> str:
    """Bedrock may return content as a list of blocks; normalise to a string."""
    content = msg.content
    if isinstance(content, str):
        return content
    return "".join(
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    )


async def prepare_research_node(state: TripState) -> dict:
    task = (
        f"Trip request:\n{state['request'].model_dump_json()}\n\n"
        f"City plan:\n{state['city_plan'].model_dump_json()}"
    )
    return {"messages": [HumanMessage(content=task)]}


async def research_agent_node(state: TripState) -> dict:
    response = await get_agent_llm().ainvoke(
        [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
    )
    return {"messages": [response]}


async def save_notes_node(state: TripState) -> dict:
    return {"research_notes": message_text(state["messages"][-1])}
