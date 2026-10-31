from langgraph.graph import END, START, StateGraph

from app.graph.nodes.allocator import city_allocator_node
from app.graph.nodes.builder import itinerary_builder_node
from app.graph.nodes.intake import intake_node
from app.graph.state import TripState


def build_graph():
    builder = StateGraph(TripState)

    builder.add_node("intake", intake_node)
    builder.add_node("city_allocator", city_allocator_node)
    builder.add_node("itinerary_builder", itinerary_builder_node)

    builder.add_edge(START, "intake")
    builder.add_edge("intake", "city_allocator")
    builder.add_edge("city_allocator", "itinerary_builder")
    builder.add_edge("itinerary_builder", END)

    return builder.compile()
