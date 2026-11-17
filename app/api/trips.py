import logging
import uuid

from fastapi import APIRouter, HTTPException, Request
from langchain_core.callbacks import get_usage_metadata_callback
from langgraph.errors import GraphRecursionError
from langgraph.types import Command

from app.schemas.plan import (
    CheckpointOut,
    ResumeIn,
    RewindIn,
    TripIn,
    TripResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/trips", tags=["trips"])


def _config(thread_id: str, checkpoint_id: str | None = None) -> dict:
    configurable = {"thread_id": thread_id}
    if checkpoint_id:
        configurable["checkpoint_id"] = checkpoint_id
    return {"configurable": configurable, "recursion_limit": 30}


def _pending(snapshot) -> dict | None:
    """Payload of the interrupt the graph is currently waiting on, if any."""
    for task in snapshot.tasks:
        for pending in task.interrupts:
            return pending.value
    return None


def _build_response(thread_id: str, snapshot) -> TripResponse:
    values = snapshot.values
    pending = _pending(snapshot)
    itinerary = values.get("itinerary")
    total = sum(d.estimated_cost for d in itinerary.days) if itinerary else None

    questions: list[str] = []
    if pending and pending.get("type") == "questions":
        status, questions = "needs_input", pending["questions"]
    elif pending and pending.get("type") == "approval":
        status = "awaiting_approval"
    elif values.get("missing_required"):
        status, questions = "incomplete", values.get("questions", [])
    else:
        status = "complete"

    return TripResponse(
        thread_id=thread_id,
        status=status,
        request=values.get("request"),
        questions=questions,
        assumptions=values.get("assumptions", []),
        warnings=values.get("warnings", []),
        attempts=values.get("attempts"),
        revisions=values.get("revisions", 0),
        approved=values.get("approved"),
        estimated_total=total,
        city_plan=values.get("city_plan"),
        itinerary=itinerary,
    )


def _summarize_usage(usage_metadata: dict) -> dict:
    """Sum token usage across all models used in one graph run."""
    totals = {"input": 0, "output": 0, "total": 0, "reasoning": 0, "cached": 0}
    for model_usage in usage_metadata.values():
        totals["input"] += model_usage.get("input_tokens", 0)
        totals["output"] += model_usage.get("output_tokens", 0)
        totals["total"] += model_usage.get("total_tokens", 0)
        totals["reasoning"] += (model_usage.get("output_token_details") or {}).get(
            "reasoning", 0
        )
        totals["cached"] += (model_usage.get("input_token_details") or {}).get(
            "cache_read", 0
        )
    return totals


def resume_value(pending: dict, body: ResumeIn):
    """Validate the body against the pending interrupt; return the value for Command(resume=...)."""
    kind = pending.get("type")
    if kind == "questions":
        if not body.answer or not body.answer.strip():
            raise HTTPException(
                status_code=422, detail="'answer' is required to answer the questions."
            )
        return body.answer.strip()
    if kind == "approval":
        if body.approved is None:
            raise HTTPException(
                status_code=422, detail="'approved' (true/false) is required."
            )
        if body.approved is False and not (body.feedback or "").strip():
            raise HTTPException(
                status_code=422, detail="'feedback' is required when approved is false."
            )
        return {"approved": body.approved, "feedback": body.feedback}
    raise HTTPException(status_code=500, detail=f"Unknown interrupt type: {kind}")


async def _run(
    graph, graph_input, thread_id: str, checkpoint_id: str | None = None
) -> dict:
    config = _config(thread_id, checkpoint_id)
    with get_usage_metadata_callback() as usage:
        try:
            await graph.ainvoke(graph_input, config=config)
        except GraphRecursionError:
            logger.error("thread_id=%s hit the recursion limit", thread_id)
            raise HTTPException(status_code=500, detail="Planning took too many steps.")
        finally:
            totals = _summarize_usage(usage.usage_metadata)
            logger.info(
                "thread_id=%s token usage: total=%d (input=%d, output=%d, of which reasoning=%d, cached input=%d)",
                thread_id,
                totals["total"],
                totals["input"],
                totals["output"],
                totals["reasoning"],
                totals["cached"],
            )
            logger.debug(
                "thread_id=%s token usage per model: %s",
                thread_id,
                usage.usage_metadata,
            )
    return totals


async def _load(graph, thread_id: str):
    snapshot = await graph.aget_state(_config(thread_id))
    if not snapshot.values:
        logger.warning("thread_id=%s not found", thread_id)
        raise HTTPException(status_code=404, detail="Trip not found")
    return snapshot


@router.post("", response_model=TripResponse)
async def create_trip(body: TripIn, request: Request) -> TripResponse:
    graph = request.app.state.graph
    thread_id = uuid.uuid4().hex
    logger.info(
        "POST /trips: new thread_id=%s user_id=%s text=%r",
        thread_id,
        body.user_id,
        body.text[:100],
    )
    await _run(graph, {"user_text": body.text, "user_id": body.user_id}, thread_id)
    snapshot = await _load(graph, thread_id)
    response = _build_response(thread_id, snapshot)
    logger.info("POST /trips: thread_id=%s status=%s", thread_id, response.status)
    return response


@router.get("/{thread_id}", response_model=TripResponse)
async def get_trip(thread_id: str, request: Request) -> TripResponse:
    logger.info("GET /trips/%s", thread_id)
    snapshot = await _load(request.app.state.graph, thread_id)
    return _build_response(thread_id, snapshot)


@router.post("/{thread_id}/resume", response_model=TripResponse)
async def resume_trip(thread_id: str, body: ResumeIn, request: Request) -> TripResponse:
    graph = request.app.state.graph
    snapshot = await _load(graph, thread_id)
    pending = _pending(snapshot)
    if pending is None:
        logger.warning(
            "Resume rejected: thread_id=%s is not waiting for input", thread_id
        )
        raise HTTPException(
            status_code=409, detail="This trip is not waiting for input."
        )

    logger.info(
        "POST /trips/%s/resume: pending type=%s", thread_id, pending.get("type")
    )
    value = resume_value(pending, body)

    await _run(graph, Command(resume=value), thread_id)
    snapshot = await _load(graph, thread_id)
    response = _build_response(thread_id, snapshot)
    logger.info("Resume done: thread_id=%s status=%s", thread_id, response.status)
    return response


@router.get("/{thread_id}/history", response_model=list[CheckpointOut])
async def trip_history(
    thread_id: str, request: Request, limit: int = 50
) -> list[CheckpointOut]:
    graph = request.app.state.graph
    logger.info("GET /trips/%s/history limit=%d", thread_id, limit)
    items: list[CheckpointOut] = []
    async for snap in graph.aget_state_history(_config(thread_id)):  # newest first
        items.append(
            CheckpointOut(
                checkpoint_id=snap.config["configurable"]["checkpoint_id"],
                step=snap.metadata.get("step"),
                source=snap.metadata.get("source"),
                next=list(snap.next),
                created_at=snap.created_at,
            )
        )
        if len(items) >= limit:
            break
    if not items:
        raise HTTPException(status_code=404, detail="Trip not found")
    return items


@router.post("/{thread_id}/rewind", response_model=TripResponse)
async def rewind_trip(thread_id: str, body: RewindIn, request: Request) -> TripResponse:
    graph = request.app.state.graph
    logger.info(
        "POST /trips/%s/rewind to checkpoint_id=%s", thread_id, body.checkpoint_id
    )

    target = None
    async for snap in graph.aget_state_history(_config(thread_id)):
        if snap.config["configurable"]["checkpoint_id"] == body.checkpoint_id:
            target = snap
            break
    if target is None:
        raise HTTPException(
            status_code=404, detail="Checkpoint not found for this trip."
        )
    if not target.next:
        raise HTTPException(
            status_code=409, detail="Nothing to re-run from that checkpoint."
        )

    logger.warning(
        "Replaying from checkpoint %s (next=%s). Nodes after it re-run, including LLM calls.",
        body.checkpoint_id,
        list(target.next),
    )
    await _run(graph, None, thread_id, checkpoint_id=body.checkpoint_id)
    snapshot = await _load(graph, thread_id)
    return _build_response(thread_id, snapshot)
