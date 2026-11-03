from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import parse, tools, trips
from app.graph.build import build_graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.graph = build_graph()  # compile once, reuse for every request
    yield


app = FastAPI(title="Trip Planner API", lifespan=lifespan)
app.include_router(parse.router)
app.include_router(trips.router)
app.include_router(tools.router)


@app.get("/health")
def health():
    return {"status": "ok"}
