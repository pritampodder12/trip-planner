import logging

from langgraph.types import interrupt

from app.core.logging_config import log_call
from app.graph.state import TripState

logger = logging.getLogger(__name__)

MAX_CLARIFY_ROUNDS = 3

OPTIONAL_NOTES = {
    "budget": "No budget was given, so suggestions assume a mid-range budget.",
    "start_date": "No start date was given, so weather is not date-specific.",
    "interest": "No interests were given, so a general mix of sights and food is planned.",
}


@log_call("node")
def validate_request_node(state: TripState) -> dict:
    req = state["request"]

    missing: list[str] = []
    if not req.cities:
        missing.append("cities")
    if req.days < 1:
        missing.append("days")
    elif req.cities and req.days < len(req.cities):
        missing.append("days_too_few")

    assumptions: list[str] = []
    if req.budget is None:
        assumptions.append(OPTIONAL_NOTES["budget"])
    if req.start_date is None:
        assumptions.append(OPTIONAL_NOTES["start_date"])
    if not req.interests:
        assumptions.append(OPTIONAL_NOTES["interest"])

    logger.info(
        "Validation: cities=%s days=%s missing_required=%s assumptions=%d",
        req.cities,
        req.days,
        missing,
        len(assumptions),
    )
    return {"missing_required": missing, "assumptions": assumptions}


def route_after_validation(state: TripState) -> str:
    # OLD CODE

    # """Conditional edge: returns the NAME of the next node."""
    # next_node = "ask_user" if state.get("missing_required") else "city_allocator"
    # return next_node

    # New Phase 4 change
    missing = state.get("missing_required")
    rounds = state.get("clarify_rounds", 0)
    if not missing:
        logger.info("Router: request is complete -> city_allocator")
        return "city_allocator"
    if rounds >= MAX_CLARIFY_ROUNDS:
        logger.warning(
            "Router: still missing %s after %d rounds -> give_up", missing, rounds
        )
        return "give_up"
    logger.info("Router: missing %s -> ask_user (round %d)", missing, rounds + 1)
    return "ask_user"


def _build_questions(state: TripState) -> list[str]:
    req = state["request"]
    questions: list[str] = []
    for item in state["missing_required"]:
        if item == "cities":
            questions.append("Which cities would you like to visit?")
        elif item == "days":
            questions.append("How many days in the trip")
        elif item == "days_too_few":
            questions.append(
                f"You listed {len(req.cities)} cities but only {req.days} days. "
                "Can you add more days or drop a city?"
            )
        return questions


@log_call("node")
def ask_user_node(state: TripState) -> dict:
    questions = _build_questions(state)
    logger.info("Asking the user %d question(s): %s", len(questions), questions)

    # PAUSE. The payload goes to the API caller; the run resumes with their answer.
    answer = interrupt({"type": "questions", "questions": questions})

    # Everything below runs only after the user has answered.
    logger.info("User answered the clarification (%d characters)", len(str(answer)))
    new_text = f"{state['user_text']}\nAdditional details from the traveler: {answer}"

    return {
        "user_text": new_text,
        "clarify_rounds": state.get("clarify_rounds", 0) + 1,
        "questions": questions,
    }
