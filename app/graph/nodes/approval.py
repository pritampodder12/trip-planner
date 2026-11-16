import logging

from langgraph.types import interrupt

from app.core.logging_config import log_call
from app.graph.state import TripState

logger = logging.getLogger(__name__)

MAX_REVISIONS = 3


@log_call("node")
def human_review_node(state: TripState) -> dict:
    itinerary = state["itinerary"]
    total = sum(d.estimated_cost for d in itinerary.days)
    warnings = state.get("warnings", [])
    logger.info(
        "Asking the human to review: %d days, estimated total %.0f, %d warning(s), revisions so far %d",
        len(itinerary.days),
        total,
        len(warnings),
        state.get("revisions", 0),
    )

    # PAUSE. Payload must be JSON-serializable (plain dicts and lists).
    decision = interrupt(
        {
            "type": "approval",
            "estimated_total": total,
            "warnings": warnings,
            "itinerary": itinerary.model_dump(),
        }
    )

    if decision.get("approved"):
        logger.info("Itinerary approved by the user")
        return {"approved": True}

    feedback = (
        decision.get("feedback") or ""
    ).strip() or "Please improve the itinerary."
    revisions = state.get("revisions", 0) + 1
    logger.info("User asked for changes (revision %d): %s", revisions, feedback[:200])

    update = {
        "approved": False,
        "revisions": revisions,
        "attempts": 0,
        "validation_errors": [f"The traveller asked for the change: {feedback}"],
        "feedback_log": state.get("feedback_log", []) + [feedback],  # new
    }
    if revisions >= MAX_REVISIONS:
        logger.warning(
            "Maximum revisions reached (%d); finishing with the latest version",
            revisions,
        )
        update["warnings"] = warnings + [
            f"Maximum of {MAX_REVISIONS} revisions reached; this is the latest version."
        ]
    return update


def route_after_approval(state: TripState) -> str:
    if state.get("approved"):
        logger.info("Router: approved -> done")
        return "done"
    if state.get("revisions", 0) >= MAX_REVISIONS:
        logger.info("Router: revision cap reached -> done")
        return "done"
    logger.info("Router: changes requested -> itinerary_builder")
    return "itinerary_builder"
