import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.store.memory import InMemoryStore

from app.api import parse, tools, trip_stream, trips, users
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.graph.build import build_graph

setup_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting up: opening checkpoint database at %s", settings.checkpoint_db
    )
    Path(settings.checkpoint_db).parent.mkdir(parents=True, exist_ok=True)
    # Must be `async with`: the saver owns an open DB connection.
    async with AsyncSqliteSaver.from_conn_string(
        settings.checkpoint_db
    ) as checkpointer:
        store = InMemoryStore()  # lost on restart; the Postgres store comes in Phase 7
        app.state.store = store
        app.state.graph = build_graph(checkpointer, store)
        logger.info("Graph compiled with SQLite checkpointer and in-memory store")
        yield
    logger.info("Shutting down: checkpoint database closed")


app = FastAPI(title="Trip Planner API", lifespan=lifespan)
app.include_router(parse.router)
app.include_router(trips.router)
app.include_router(tools.router)
app.include_router(trip_stream.router)
app.include_router(users.router)


@app.get("/health")
def health():
    return {"status": "ok"}
