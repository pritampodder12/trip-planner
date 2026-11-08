from app.graph.nodes.review import (
    MAX_ATTEMPTS,
    review_itinerary_node,
    route_after_review,
)
from app.schemas.plan import CityPlan, CityStay, DayPlan, Itinerary
from app.schemas.trip import TripRequest


def day(n, city="Jaipur", cost=1000):
    return DayPlan(
        day=n,
        city=city,
        morning="Amber Fort",
        afternoon="Lunch",
        evening="Bazaar",
        estimated_cost=cost,
    )


def make_state(days, budget=None, trip_days=2):
    return {
        "request": TripRequest(cities=["Jaipur"], days=trip_days, budget=budget),
        "city_plan": CityPlan(
            stays=[CityStay(city="Jaipur", days=trip_days)], reasoning="test"
        ),
        "itinerary": Itinerary(days=days),
        "city_notes": {
            "Jaipur": {"city": "Jaipur", "notes": "", "places": ["Amber Fort"]}
        },
    }


def test_valid_itinerary_has_no_errors():
    out = review_itinerary_node(make_state([day(1), day(2)], budget=5000))
    assert out["validation_errors"] == []


def test_wrong_day_count():
    assert review_itinerary_node(make_state([day(1)]))["validation_errors"]


def test_over_budget():
    out = review_itinerary_node(
        make_state([day(1, cost=4000), day(2, cost=4000)], budget=5000)
    )
    assert any("budget" in e for e in out["validation_errors"])


def test_retry_cap():
    assert (
        route_after_review({"validation_errors": ["x"], "attempts": 1})
        == "itinerary_builder"
    )
    assert (
        route_after_review({"validation_errors": ["x"], "attempts": MAX_ATTEMPTS})
        == "finalize"
    )
