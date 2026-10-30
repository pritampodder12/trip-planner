from fastapi import FastAPI

from app.api import parse

app = FastAPI(title="Trip Planner API")
app.include_router(parse.router)


@app.get("/health")
def health():
    return {"status": "ok"}
