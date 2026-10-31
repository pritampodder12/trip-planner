import asyncio

from app.graph.build import build_graph


async def main():
    graph = build_graph()

    print(graph.get_graph().draw_mermaid())

    text = "5 days in Jaipur and Udaipur, 40k budget, love food and forts, 2 people"
    async for update in graph.astream({"user_text": text}, stream_mode="updates"):
        for node, output in update.items():
            print(f"\n=== {node} ===")
            print(output)


asyncio.run(main())
