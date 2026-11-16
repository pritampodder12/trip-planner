import asyncio
import time

from app.graph.build import build_graph


async def main():
    graph = build_graph()
    print(graph.get_graph().draw_mermaid())  # paste into https://mermaid.live

    text = "5 days in Jaipur, Udaipur and Jodhpur, 60k budget, love food and forts, 2 people"
    start = last = time.perf_counter()
    async for update in graph.astream(
        {"user_text": text}, stream_mode="updates", config={"recursion_limit": 30}
    ):
        now = time.perf_counter()
        for node, output in update.items():
            keys = list(output.keys()) if output else output
            print(f"[{now - start:6.1f}s  +{now - last:5.1f}s] {node} -> {keys}")
        last = now


asyncio.run(main())
