import asyncio
import time

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from app.core.logging_config import setup_logging
from app.graph.build import build_graph

setup_logging("WARNING")  # keep the console readable; we print the events ourselves


async def main():
    graph = build_graph(InMemorySaver(), InMemoryStore())
    config = {"configurable": {"thread_id": "stream-1"}, "recursion_limit": 30}
    text = "4 days in Jaipur and Udaipur, 40000 INR, 2 people, love food and forts"
    start = time.perf_counter()

    async for part in graph.astream(
        {"user_text": text, "user_id": "demo"},
        config,
        stream_mode=["updates", "custom"],
        subgraphs=True,
    ):
        ns, mode, data = part if len(part) == 3 else ((), part[0], part[1])
        t = time.perf_counter() - start
        if mode == "custom":
            print(f"[{t:5.1f}s] progress  {data}")
        else:
            for node in data:
                where = "/".join(ns) if ns else "top"
                print(f"[{t:5.1f}s] node      {node}  ({where})")


asyncio.run(main())
