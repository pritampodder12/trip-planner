from datetime import date

from pydantic import BaseModel, Field


class TripRequest(BaseModel):
    """Structured version of what the user wants."""

    cities: list[str] = Field(description="Cities to visit, in the order mentioned")
    days: int = Field(description="Total number of trip days")
    budget: float | None = Field(
        default=None, description="Total budget as a plain number"
    )
    currency: str = Field(default="INR", description="Currency code of the budget")
    interests: list[str] = Field(
        default_factory=list, description="e.g. food, forts, nightlife"
    )
    travelers: int = Field(default=1, description="Number of travellers")
    start_date: date | None = Field(
        default=None, description="Trip start date if started"
    )
    missing_info: list[str] = Field(
        default_factory=list,
        description="Important details the user did NOT provide",
    )
