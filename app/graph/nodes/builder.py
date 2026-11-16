import logging
from functools import lru_cache

from langchain_core.prompts import ChatPromptTemplate

from app.core.llm import get_llm
from app.core.logging_config import log_call
from app.core.memory import format_profile
from app.core.progress import emit_progress
from app.graph.state import TripState
from app.schemas.plan import Itinerary

logger = logging.getLogger(__name__)

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a travel planner. Create a day-by-day itinerary that follows the city "
            "plan exactly: same city order, same number of days per city, day numbers 1..N "
            "with no gaps. Match the traveler's interests and budget. Keep each time slot "
            "to one or two sentences. For every day give estimated_cost for ALL travelers "
            "together in the budget currency; the sum over all days must stay within the "
            "budget. Use ONLY places named in the research notes; if something is missing "
            "write 'to be confirmed'. Mention weather and travel time where the notes "
            "provide them. Respect the traveler profile (diet, pace, dislikes, past change requests) "
            "when choosing activities.",
        ),
        (
            "human",
            "Trip request:\n{request_json}\n\nCity plan:\n{plan_json}\n\n"
            "\n\nTraveler profile:\n{profile}"
            "Research notes per city:\n{notes}\n\nFeedback:\n{feedback}",
        ),
    ]
)


@lru_cache
def get_chain():
    return prompt | get_llm().with_structured_output(Itinerary)


def _format_notes(state: TripState) -> str:
    notes = state.get("city_notes", {})
    parts = []
    for stay in state["city_plan"].stays:
        n = notes.get(stay.city)
        if n:
            parts.append(f"### {stay.city} ({stay.days}) days\n{n['notes']}")
        else:
            parts.append(f"### {stay.city} ({stay.days} days)\nNo research available.")
        return "\n\n".join(parts)


@log_call("node")
async def itinerary_builder_node(state: TripState) -> dict:
    emit_progress(
        "build", f"Building the itinerary (attempt {state.get('attempts', 0) + 1})"
    )
    errors = state.get("validation_errors") or []
    if errors and state.get("itinerary"):
        feedback = (
            "Your previous itinerary had these problems. Fix ALL of them and keep the rest:\n- "
            + "\n- ".join(errors)
            + "\n\nPrevious itinerary:\n"
            + state["itinerary"].model_dump_json()
        )
    else:
        feedback = "None. This is the first attempt."

    itinerary = await get_chain().ainvoke(
        {
            "request_json": state["request"].model_dump_json(),
            "plan_json": state["city_plan"].model_dump_json(),
            "notes": _format_notes(state),
            "feedback": feedback,
            "profile": format_profile(state.get("preferences")),
        }
    )
    # logger.info("[node] itinerary_builder | done | total_days=%d", len(itinerary.days))
    return {"itinerary": itinerary, "attempts": state.get("attempts", 0) + 1}
