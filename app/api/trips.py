from fastapi import APIRouter, Request

from app.schemas.plan import TripIn, TripResponse

router = APIRouter(prefix="/trips", tags=["trips"])


@router.post("", response_model=TripResponse)
async def create_trip(body: TripIn, request: Request) -> TripResponse:
    result = await request.app.state.graph.ainvoke({"user_text": body.text})
    return TripResponse(
        request=result["request"],
        city_plan=result["city_plan"],
        itinerary=result["itinerary"],
    )
