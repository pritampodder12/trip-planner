def format_questions(data: dict) -> str:
    """Formats the clarification questions the LLM is asking."""
    questions = data.get("questions", [])
    if not questions:
        return "I need a bit more information. Could you give me more details about your trip?"

    lines = ["I need a bit more info:\n"]
    for q in questions:
        lines.append(f"• {q}")

    assumptions = data.get("assumptions", [])
    if assumptions:
        lines.append("\nI'll assume:")
        for a in assumptions:
            lines.append(f"  ✓ {a}")

    return "\n".join(lines)


def format_itinerary(data: dict) -> str:
    """Formats the full itinerary for the approval message."""
    lines = []

    # --- Header ---
    req = data.get("request") or {}
    cities = (
        ", ".join(req.get("cities", [])) if req.get("cities") else "your destination"
    )
    days = req.get("days", "?")
    lines.append(f"🗺 *Trip Plan: {cities} ({days} days)*\n")

    # --- City allocation ---
    city_plan = data.get("city_plan")
    if city_plan:
        lines.append("*City allocation:*")
        for stay in city_plan.get("stays", []):
            lines.append(f"  📍 {stay['city']} — {stay['days']} day(s)")
        lines.append("")

    # --- Day-by-day itinerary ---
    itinerary = data.get("itinerary")
    if itinerary:
        lines.append("*Day-by-day plan:*\n")
        for day in itinerary.get("days", []):
            lines.append(f"📅 *Day {day['day']} — {day['city']}*")
            lines.append(f"  🌅 Morning: {day['morning']}")
            lines.append(f"  ☀️  Afternoon: {day['afternoon']}")
            lines.append(f"  🌙 Evening: {day['evening']}")
            if day.get("food_tip"):
                lines.append(f"  🍽  Food tip: {day['food_tip']}")
            if day.get("estimated_cost"):
                lines.append(f"  💰 Est. cost: {day['estimated_cost']:.0f}")
            lines.append("")

    # --- Total cost ---
    total = data.get("estimated_total")
    if total:
        currency = req.get("currency", "")
        lines.append(f"💵 *Estimated total: {total:.0f} {currency}*\n")

    # --- Warnings & assumptions ---
    warnings = data.get("warnings", [])
    if warnings:
        lines.append("⚠️ Notes:")
        for w in warnings:
            lines.append(f"  • {w}")
        lines.append("")

    assumptions = data.get("assumptions", [])
    if assumptions:
        lines.append("ℹ️ Assumptions made:")
        for a in assumptions:
            lines.append(f"  • {a}")
        lines.append("")

    lines.append("Happy with this plan? Tap a button below 👇")

    result = "\n".join(lines)

    # Telegram's hard limit is 4096 chars — truncate if needed
    if len(result) > 4000:
        result = result[:3950] + "\n\n..._(plan is long, truncated)_"

    return result
