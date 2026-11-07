import logging
import time

from fastapi import APIRouter, HTTPException, Request
from langchain_core.callbacks import get_usage_metadata_callback
from langgraph.errors import GraphRecursionError

from app.schemas.plan import TripIn, TripResponse

router = APIRouter(prefix="/trips", tags=["trips"])

logger = logging.getLogger(__name__)


@router.post("", response_model=TripResponse)
async def create_trip(body: TripIn, request: Request) -> TripResponse:
    graph = request.app.state.graph
    started = time.perf_counter()

    with get_usage_metadata_callback() as cb:
        try:
            result = await graph.ainvoke(
                {"user_text": body.text},
                config={"recursion_limit": 30},
            )
        except GraphRecursionError:
            raise HTTPException(
                status_code=500,
                detail="Planning took too many steps. Try a simpler request.",
            )
        finally:
            total = sum(u["total_tokens"] for u in cb.usage_metadata.values())
            logger.info("[usage] total_tokens=%s", total)
            logger.info("[usage] duration_s=%.1f", time.perf_counter() - started)
            logger.info("[usage] details=%s", cb.usage_metadata)

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
