import functools
import inspect
import logging
import time

# Exceptions LangGraph uses to pause a node; these are not errors.
PAUSE_EXCEPTIONS = {"GraphInterrupt", "NodeInterrupt", "GraphBubbleUp", "ParentCommand"}

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    for noisy in ("httpx", "httpcore", "openai", "urllib3", "aiosqlite", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    logger.info("Logging configured at level %s", level.upper())


def _short(value, limit: int = 200) -> str:
    text = repr(value)
    return text if len(text) <= limit else text[:limit] + "..."


def log_call(kind: str = "node", log_args: bool = False):
    """Decorator: logs 'node X called', 'finished (1.2s)', 'paused' or 'failed'.

    Use kind="node" on graph nodes and kind="tool" (log_args=True) under @tool.
    """

    def decorator(func):
        log = logging.getLogger(func.__module__)
        label = f"{kind} {func.__name__}"

        def before(kwargs):
            if log_args and kwargs:
                log.info("%s called with %s", label, _short(kwargs))
            else:
                log.info("%s called", label)
            return time.perf_counter()

        def failed(exc, start):
            if type(exc).__name__ in PAUSE_EXCEPTIONS:
                log.info("%s paused (waiting for human input)", label)
            else:
                log.exception(
                    "%s failed after %.1fs", label, time.perf_counter() - start
                )

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start = before(kwargs)
                try:
                    result = await func(*args, **kwargs)
                except Exception as exc:
                    failed(exc, start)
                    raise
                log.info("%s finished (%.1fs)", label, time.perf_counter() - start)
                return result

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = before(kwargs)
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                failed(exc, start)
                raise
            log.info("%s finished (%.1fs)", label, time.perf_counter() - start)
            return result

        return sync_wrapper

    return decorator
