from app.graph.state import TripState

OPTIONAL_NOTES = {
    "budget": "No budget was given, so suggestions assume a mid-range budget.",
    "start_date": "No start date was given, so weather is not date-specific.",
    "interest": "No interests were given, so a general mix of sights and food is planned.",
}


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

    return {"missing_required": missing, "assumptions": assumptions}


def route_after_validation(state: TripState) -> str:
    """Conditional edge: returns the NAME of the next node."""
    return "ask_user" if state.get("missing_required") else "city_allocator"


def ask_user_node(state: TripState) -> dict:
    req = state["request"]
    questions: list[str] = []
    for item in state["missing_required"]:
        if item == "cities":
            questions.append("Which cities would you like to visit?")
        elif item == "days":
            questions.append("How many days is the trip?")
        elif item == "days_too_few":
            questions.append(
                f"You listed {len(req.cities)} cities but only {req.days} days."
                "Can you add more days or drop a city?"
            )
    return {"questions": questions}
