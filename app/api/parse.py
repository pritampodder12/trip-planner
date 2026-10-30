from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.graph.nodes.intake import parse_trip_request
from app.schemas.trip import TripRequest

router = APIRouter(tags=["parse"])


class ParseIn(BaseModel):
    text: str = Field(min_length=3, max_length=2000)


@router.post("/parse-request", response_model=TripRequest)
async def parse_request(body: ParseIn) -> TripRequest:
    return await parse_trip_request(body.text)
