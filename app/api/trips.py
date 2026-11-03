from fastapi import APIRouter, HTTPException, Request
from langgraph.errors import GraphRecursionError

from app.schemas.plan import TripIn, TripResponse

router = APIRouter(prefix="/trips", tags=["trips"])


@router.post("", response_model=TripResponse)
async def create_trip(body: TripIn, request: Request) -> TripResponse:
    graph = request.app.state.graph
    try:
        result = await graph.ainvoke(
            {"user_text": body.text},
            config={"recursion_limit": 30},
        )
    except GraphRecursionError:
        raise HTTPException(
            status_code=500,
            details="Planning took too many steps. Try a simpler request.",
        )

    if result.get("missing_required"):
        return TripResponse(
            status="needs_input",
            request=result["request"],
            questions=result["questions"],
        )

    return TripResponse(
        status="complete",
        request=result["request"],
        assumptions=result.get("assumptions", []),
        city_plan=result["city_plan"],
        itinerary=result["itinerary"],
    )
