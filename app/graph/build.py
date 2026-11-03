from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.graph.nodes.allocator import city_allocator_node
from app.graph.nodes.builder import itinerary_builder_node
from app.graph.nodes.intake import intake_node
from app.graph.nodes.research import (
    prepare_research_node,
    research_agent_node,
    save_notes_node,
)
from app.graph.nodes.validate import (
    ask_user_node,
    route_after_validation,
    validate_request_node,
)
from app.graph.state import TripState
from app.tools import ALL_TOOLS


def build_graph():
    builder = StateGraph(TripState)

    builder.add_node("intake", intake_node)
    builder.add_node("validate_request", validate_request_node)
    builder.add_node("ask_user", ask_user_node)
    builder.add_node("city_allocator", city_allocator_node)
    builder.add_node("prepare_research", prepare_research_node)
    builder.add_node("research_agent", research_agent_node)
    builder.add_node("tools", ToolNode(ALL_TOOLS))
    builder.add_node("save_notes", save_notes_node)
    builder.add_node("itinerary_builder", itinerary_builder_node)

    builder.add_edge(START, "intake")
    builder.add_edge("intake", "validate_request")

    # Conditional edge #1: enough info to plan?
    builder.add_conditional_edges(
        "validate_request",
        route_after_validation,
        {"ask_user": "ask_user", "city_allocator": "city_allocator"},
    )
    builder.add_edge("ask_user", END)

    builder.add_edge("city_allocator", "prepare_research")
    builder.add_edge("prepare_research", "research_agent")

    # Conditional edge #2: did the LLM request tools? (the ReAct loop)
    builder.add_conditional_edges(
        "research_agent",
        tools_condition,
        {"tools": "tools", END: "save_notes"},
    )
    builder.add_edge("tools", "research_agent")  # the cycle

    builder.add_edge("save_notes", "itinerary_builder")
    builder.add_edge("itinerary_builder", END)

    return builder.compile()
