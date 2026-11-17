import json
import logging
import time
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.callbacks import UsageMetadataCallbackHandler
from langgraph.errors import GraphRecursionError
from langgraph.types import Command

from app.api.trips import (
    _build_response,
    _config,
    _load,
    _pending,
    _summarize_usage,
    resume_value,
)
from app.schemas.plan import ResumeIn, TripIn

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/trips", tags=["trips-stream"])


def _sse(event: str, data) -> str:
    """Format one Server-Sent Event."""
    return (
        f"event: {event}\ndata: {json.dumps(data, default=str, ensure_ascii=False)}\n\n"
    )


def _unpack(part):
    """v1 stream format with several modes and subgraphs=True: (namespace, mode, data)."""
    if len(part) == 3:
        return part
    return (), part[0], part[1]


async def _event_stream(graph, graph_input, thread_id: str) -> AsyncIterator[str]:
    usage = UsageMetadataCallbackHandler()
    config = _config(thread_id)
    config["callbacks"] = [usage]  # explicit handler: safe across generator boundaries
    started = time.perf_counter()
    counts = {"progress": 0, "node": 0}
    logger.info("SSE stream opened for thread_id=%s", thread_id)

    yield _sse("started", {"thread_id": thread_id})
    try:
        async for part in graph.astream(
            graph_input,
            config=config,
            stream_mode=["updates", "custom"],
            subgraphs=True,
        ):
            ns, mode, data = _unpack(part)
            if mode == "custom":
                counts["progress"] += 1
                yield _sse("progress", data)
            elif mode == "updates" and not ns:  # top-level nodes only
                for node in data:
                    if not node.startswith("__"):  # skip "__interrupt__"
                        counts["node"] += 1
                        yield _sse("node", {"node": node})

        snapshot = await graph.aget_state(_config(thread_id))
        response = _build_response(thread_id, snapshot)
        logger.info(
            "SSE stream finished: thread_id=%s status=%s", thread_id, response.status
        )
        yield _sse("result", response.model_dump(mode="json"))
    except GraphRecursionError:
        logger.error("SSE stream: thread_id=%s hit the recursion limit", thread_id)
        yield _sse("error", {"detail": "Planning took too many steps."})
    except Exception:
        logger.exception("SSE stream failed for thread_id=%s", thread_id)
        yield _sse("error", {"detail": "Unexpected error while planning."})
    finally:
        totals = _summarize_usage(usage.usage_metadata)
        logger.info(
            "SSE stream closed: thread_id=%s %.1fs events=%s token total=%d (reasoning=%d)",
            thread_id,
            time.perf_counter() - started,
            counts,
            totals["total"],
            totals["reasoning"],
        )


def _streaming_response(events: AsyncIterator[str]) -> StreamingResponse:
    return StreamingResponse(
        events,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/stream")
async def create_trip_stream(body: TripIn, request: Request) -> StreamingResponse:
    graph = request.app.state.graph
    thread_id = uuid.uuid4().hex
    logger.info(
        "POST /trips/stream: new thread_id=%s user_id=%s", thread_id, body.user_id
    )
    graph_input = {"user_text": body.text, "user_id": body.user_id}
    return _streaming_response(_event_stream(graph, graph_input, thread_id))


@router.post("/{thread_id}/resume/stream")
async def resume_trip_stream(
    thread_id: str, body: ResumeIn, request: Request
) -> StreamingResponse:
    graph = request.app.state.graph
    snapshot = await _load(graph, thread_id)
    pending = _pending(snapshot)
    if pending is None:
        logger.warning(
            "Stream resume rejected: thread_id=%s is not waiting for input", thread_id
        )
        raise HTTPException(
            status_code=409, detail="This trip is not waiting for input."
        )
    value = resume_value(pending, body)
    logger.info(
        "POST /trips/%s/resume/stream: pending type=%s", thread_id, pending.get("type")
    )
    return _streaming_response(_event_stream(graph, Command(resume=value), thread_id))
