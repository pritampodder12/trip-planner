import logging
from functools import lru_cache

from langchain_core.prompts import ChatPromptTemplate

from app.core.llm import get_llm
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
            "provide them.",
        ),
        (
            "human",
            "Trip request:\n{request_json}\n\nCity plan:\n{plan_json}\n\n"
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


async def itinerary_builder_node(state: TripState) -> dict:
    # logger.info(
    #     "[node] itinerary_builder | cities=%s",
    #     [s.city for s in state["city_plan"].stays],
    # )
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
        }
    )
    # logger.info("[node] itinerary_builder | done | total_days=%d", len(itinerary.days))
    return {"itinerary": itinerary, "attempts": state.get("attempts", 0) + 1}
