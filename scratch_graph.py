import asyncio

from app.graph.build import build_graph


async def main():
    graph = build_graph()
    print(graph.get_graph().draw_mermaid())  # paste into https://mermaid.live

    text = "5 days in Jaipur and Udaipur, 40k budget, love food and forts, 2 people"
    async for update in graph.astream(
        {"user_text": text}, stream_mode="updates", config={"recursion_limit": 30}
    ):
        for node, output in update.items():
            keys = list(output.keys()) if output else output
            print(f"=== {node} -> {keys}")
            if node == "tools":
                for m in output["messages"]:
                    print("   ", m.name, ":", str(m.content)[:120].replace("\n", " "))


asyncio.run(main())
