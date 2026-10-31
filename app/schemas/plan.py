from pydantic import BaseModel, Field

from app.schemas.trip import TripRequest


class TripIn(BaseModel):
    text: str = Field(min_length=3, max_length=2000)


class CityStay(BaseModel):
    city: str
    days: int = Field(description="Number of days spend in this city")


class CityPlan(BaseModel):
    stays: list[CityStay] = Field(
        description="Cities in travel order. Days must add up to total trip days."
    )
    reasoning: str = Field(
        description="One or two sentences on why this order and split"
    )


class DayPlan(BaseModel):
    day: int = Field(description="Day number starting from 1")
    city: str
    morning: str
    afternoon: str
    evening: str
    food_trip: str | None = None


class Itinerary(BaseModel):
    days: list[DayPlan]
    budget_note: str | None = Field(default=None, description="Rough budget comment")


class TripResponse(BaseModel):
    request: TripRequest
    city_plan: CityPlan
    itinerary: Itinerary
