import logging

from langgraph.config import get_stream_writer

logger = logging.getLogger(__name__)


def emit_progress(stage: str, message: str, **extra) -> None:
    """Send a progress event to clients streaming with stream_node="custom".

    A no-op when the node runs outside a graph (tests, scripts) or when nobody
    is listening for customer events.
    """

    try:
        writer = get_stream_writer()
    except Exception:
        logger.debug("emit_progress called outside a graph run: %s", message)
        return
    writer({"stage": stage, "message": message, **extra})
    logger.debug("progress emitted: %s | %s", stage, message)
