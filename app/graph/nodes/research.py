import logging

from langgraph.types import Send

from app.core.memory import format_profile
from app.graph.state import TripState

logger = logging.getLogger(__name__)


def fan_out_research(state: TripState) -> list[Send]:
    """Conditional edge: one Send per city; each starts a run of the research_city subgraph."""
    stays = state["city_plan"].stays
    profile = format_profile(state.get("preferences"))
    logger.info(
        "Fan-out: researching %d city(ies) in parallel: %s",
        len(stays),
        [s.city for s in stays],
    )
    return [
        Send(
            "research_city",
            {
                "city": stay.city,
                "days": stay.days,
                "previous_city": stays[i - 1].city if i > 0 else None,
                "profile": profile,
                "request": state["request"],
            },
        )
        for i, stay in enumerate(stays)
    ]
