from typing import Literal

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
    food_tip: str | None = None
    estimated_cost: float = Field(
        default=0,
        description="Estimated spend for this day for ALL travelers together, in the "
        "budget currency, including food and activities but excluding travel between cities",
    )


class Itinerary(BaseModel):
    days: list[DayPlan]
    budget_note: str | None = Field(default=None, description="Rough budget comment")


class ResumeIn(BaseModel):
    answer: str | None = Field(default=None, max_length=2000)
    approved: bool | None = None
    feedback: str | None = Field(default=None, max_length=1000)


class RewindIn(BaseModel):
    checkpoint_id: str


class CheckpointOut(BaseModel):
    checkpoint_id: str
    step: int | None = None
    source: str | None = None
    next: list[str]
    created_at: str | None = None


class TripResponse(BaseModel):
    thread_id: str
    status: Literal["needs_input", "awaiting_approval", "complete", "incomplete"]
    request: TripRequest | None = None
    questions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    attempts: int | None = None
    revisions: int = 0
    approved: bool | None = None
    estimated_total: float | None = None
    city_plan: CityPlan | None = None
    itinerary: Itinerary | None = None
