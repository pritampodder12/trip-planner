from typing import Annotated, TypedDict

from app.schemas.plan import CityPlan, Itinerary
from app.schemas.trip import TripRequest


def merge_dicts(left: dict | None, right: dict | None) -> dict:
    """Reducer: combine writes from parallel branches by key."""
    return {**(left or {}), **(right or {})}


class CityNotes(TypedDict):
    city: str
    notes: str
    places: list[str]


class TripState(TypedDict, total=False):
    user_text: str  # input
    request: TripRequest  # written by intake
    missing_required: list[str]  # blocking problems, decided in code
    assumptions: list[str]  # non-blocking gaps (no budget, no dates...)
    questions: list[str]  # follow-up questions for the user
    city_plan: CityPlan  # written by city_allocator
    city_notes: Annotated[dict[str, CityNotes], merge_dicts]  # filled in parallel
    # messages: Annotated[list[AnyMessage], add_messages]  # reducer: append
    # research_notes: str
    itinerary: Itinerary  # written by itinerary_builder
    attempts: int
    validation_errors: list[str]
    warnings: list[str]
    clarify_rounds: int
    revisions: int
    approved: bool
