from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

from app.schemas.plan import CityPlan, Itinerary
from app.schemas.trip import TripRequest


class TripState(TypedDict, total=False):
    user_text: str  # input
    request: TripRequest  # written by intake
    missing_required: list[str]  # blocking problems, decided in code
    assumptions: list[str]  # non-blocking gaps (no budget, no dates...)
    questions: list[str]  # follow-up questions for the user
    city_plan: CityPlan  # written by city_allocator
    messages: Annotated[list[AnyMessage], add_messages]  # reducer: append
    research_notes: str
    itinerary: Itinerary  # written by itinerary_builder
