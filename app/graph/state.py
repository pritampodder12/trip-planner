from typing import TypedDict

from app.schemas.plan import CityPlan, Itinerary
from app.schemas.trip import TripRequest


class TripState(TypedDict, total=False):
    user_text: str  # input
    request: TripRequest  # written by intake
    city_plan: CityPlan  # written by city_allocator
    itinerary: Itinerary  # written by itinerary_builder
