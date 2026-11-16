from langgraph.graph import END, START, StateGraph

from app.graph.nodes.allocator import city_allocator_node
from app.graph.nodes.approval import human_review_node, route_after_approval
from app.graph.nodes.builder import itinerary_builder_node
from app.graph.nodes.intake import intake_node
from app.graph.nodes.preferences import load_preferences_node, save_preferences_node
from app.graph.nodes.research import fan_out_research
from app.graph.nodes.review import (
    finalize_node,
    review_itinerary_node,
    route_after_review,
)
from app.graph.nodes.validate import (
    ask_user_node,
    route_after_validation,
    validate_request_node,
)
from app.graph.state import TripState
from app.graph.subgraphs.city_research import build_city_research_graph


def build_graph(checkpointer=None, store=None):
    builder = StateGraph(TripState)

    builder.add_node("intake", intake_node)
    builder.add_node("validate_request", validate_request_node)
    builder.add_node("ask_user", ask_user_node)
    builder.add_node("city_allocator", city_allocator_node)
    builder.add_node("itinerary_builder", itinerary_builder_node)
    builder.add_node("review_itinerary", review_itinerary_node)
    builder.add_node("finalize", finalize_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("load_preferences", load_preferences_node)
    builder.add_node(
        "research_city", build_city_research_graph()
    )  # a compiled subgraph as a node
    builder.add_node("save_preferences", save_preferences_node)

    # builder.add_edge(START, "intake")
    builder.add_edge(START, "load_preferences")
    builder.add_edge("load_preferences", "intake")
    builder.add_edge("intake", "validate_request")
    builder.add_conditional_edges(
        "validate_request",
        route_after_validation,
        {"ask_user": "ask_user", "city_allocator": "city_allocator", "give_up": END},
    )
    builder.add_edge("ask_user", "intake")

    # Map: one parallel research_city run per city
    builder.add_conditional_edges("city_allocator", fan_out_research, ["research_city"])
    # Reduce/fan-in: builder runs once, after ALL cities finish
    builder.add_edge("research_city", "itinerary_builder")

    # Validator loop with a cap
    builder.add_edge("itinerary_builder", "review_itinerary")
    builder.add_conditional_edges(
        "review_itinerary",
        route_after_review,
        {"itinerary_builder": "itinerary_builder", "finalize": "finalize"},
    )
    builder.add_edge("finalize", "human_review")
    builder.add_conditional_edges(
        "human_review",
        route_after_approval,
        {"itinerary_builder": "itinerary_builder", "done": "save_preferences"},
    )
    builder.add_edge("save_preferences", END)

    return builder.compile(checkpointer=checkpointer, store=store)
