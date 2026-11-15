from app.graph.nodes.approval import MAX_REVISIONS, route_after_approval
from app.graph.nodes.validate import MAX_CLARIFY_ROUNDS, route_after_validation


def test_validation_routes():
    assert route_after_validation({"missing_required": []}) == "city_allocator"
    assert (
        route_after_validation({"missing_required": ["cities"], "clarify_rounds": 0})
        == "ask_user"
    )
    assert (
        route_after_validation(
            {"missing_required": ["cities"], "clarify_rounds": MAX_CLARIFY_ROUNDS}
        )
        == "give_up"
    )


def test_approval_routes():
    assert route_after_approval({"approved": True}) == "done"
    assert (
        route_after_approval({"approved": False, "revisions": 1}) == "itinerary_builder"
    )
    assert (
        route_after_approval({"approved": False, "revisions": MAX_REVISIONS}) == "done"
    )
