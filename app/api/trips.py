import logging
import time
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
        revisions=values.get("rivisions", 0),
        approved=values.get("approved"),
        estimated_total=total,
        city_plan=values.get("city_plan"),
        itinerary=itinerary,
    )


async def _run(graph, graph_input, thread_id: str, checkpoint_id: str | None) -> None:
    config = _config(thread_id, checkpoint_id)
    started = time.perf_counter()
    with get_usage_metadata_callback() as usage:
        try:
            await graph.ainvoke(graph_input, config=config)
        except GraphRecursionError:
            logger.error("thread_id=%s hit the recursion limit", thread_id)
            raise HTTPException(status_code=500, detail="Planning took too many steps.")
        finally:
            total = sum(u["total_tokens"] for u in usage.usage_metadata.values())
            logger.info("[usage] total_tokens=%s", total)
            logger.info("[usage] duration_s=%.1f", time.perf_counter() - started)
            logger.info("[usage] details=%s", usage.usage_metadata)


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
    logger.info("POST /trips: new thread_id=%s text=%r", thread_id, body.text[:100])
    await _run(graph, {"user_text": body.text}, thread_id)
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

    kind = pending.get("type")
    logger.info("POST /trips/%s/resume: pending type=%s", thread_id, kind)
    if kind == "questions":
        if not body.answer or not body.answer.strip():
            raise HTTPException(
                status_code=422, detail="'answer' is required to answer the questions."
            )
        value = body.answer.strip()
    elif kind == "approval":
        if body.approved is None:
            raise HTTPException(
                status_code=422, detail="'approved' (true/false) is required."
            )
        if body.approved is False and not (body.feedback or "").strip():
            raise HTTPException(
                status_code=422, detail="'feedback' is required when approved is false."
            )
        value = {"approved": body.approved, "feedback": body.feedback}
    else:
        raise HTTPException(status_code=500, detail=f"Unknown interrupt type: {kind}")

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
