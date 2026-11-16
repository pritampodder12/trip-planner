from typing import Annotated, Literal

from pydantic import BaseModel, Field


class PreferencesIn(BaseModel):
    """What the traveler tells us explicitly."""

    diet: str | None = Field(
        default=None, max_length=50, description="e.g. vegetarian, no pork"
    )
    pace: Literal["relaxed", "balanced", "packed"] | None = None
    budget_style: Literal["budget", "mid-range", "luxury"] | None = None
    dislikes: list[Annotated[str, Field(max_length=50)]] = Field(
        default_factory=list, max_length=10
    )
    notes: str | None = Field(default=None, max_length=300)


class PreferencesOut(BaseModel):
    user_id: str
    preferences: dict  # explicit, set by the user
    history: dict  # learned from approved trips
