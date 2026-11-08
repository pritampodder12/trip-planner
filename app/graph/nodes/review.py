from app.graph.state import TripState

MAX_ATTEMPTS = 3


def review_itinerary_node(state: TripState) -> dict:
    req, plan, itinerary = state["request"], state["city_plan"], state["itinerary"]
    notes = state.get("city_notes", {})
    errors: list[str] = []  # trigger a retry
    warnings: list[str] = []  # reported only

    # 1. Day numbering and count
    numbers = [d.day for d in itinerary.days]
    if numbers != list(range(1, req.days + 1)):
        errors.append(
            f"The itinerary must have exactly {req.days} days numbered 1 to {req.days}, "
            f"but it has day numbers {numbers}."
        )

    # 2. City order and days per city
    expected = [s.city.lower() for s in plan.stays for _ in range(s.days)]
    actual = [d.city.lower() for d in itinerary.days]
    if actual != expected:
        errors.append(
            "Cities per day must follow this exact order: "
            + ", ".join(f"day {i + 1}: {c}" for i, c in enumerate(expected))
        )

    # 3. Empty time slots
    for d in itinerary.days:
        if not (d.morning.strip() and d.afternoon.strip() and d.evening.strip()):
            errors.append(
                f"Day {d.day} has an empty morning, afternoon or evening slot."
            )

    # 4. Budget, with the total computed here in code
    total = sum(d.estimated_cost for d in itinerary.days)
    if req.budget:
        if total == 0:
            warnings.append(
                "The itinerary has no cost estimates, so the budget was not checked."
            )
        elif total > req.budget * 1.05:
            errors.append(
                f"Estimated total {total:.0f} {req.currency} exceeds the budget of "
                f"{req.budget:.0f} {req.currency}. Choose cheaper options."
            )

    # 5. Grounding: a warning only, because names often differ slightly
    for d in itinerary.days:
        shortlist = (notes.get(d.city) or {}).get("places", [])
        text = " ".join([d.morning, d.afternoon, d.evening, d.food_tip or ""]).lower()
        if shortlist and not any(p.lower() in text for p in shortlist):
            warnings.append(
                f"Day {d.day}: no place from the {d.city} research shortlist is mentioned."
            )

    return {"validation_errors": errors, "warnings": warnings}


def route_after_review(state: TripState) -> str:
    if state.get("validation_errors") and state.get("attempts", 0) < MAX_ATTEMPTS:
        return "itinerary_builder"  # loop back with feedback
    return "finalize"


def finalize_node(state: TripState) -> dict:
    warnings = list(state.get("warnings", []))
    for e in state.get("validation_errors", []):
        warnings.append(f"Unresolved after {state.get('attempts', 0)} attempts: {e}")
    return {"warnings": warnings}
