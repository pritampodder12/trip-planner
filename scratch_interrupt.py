import asyncio

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.core.logging_config import setup_logging
from app.graph.build import build_graph

setup_logging()


def pending(snapshot):
    for task in snapshot.tasks:
        for item in task.interrupts:
            return item.value
    return None


def show(label, snapshot):
    p = pending(snapshot)
    if p is None:
        print(
            f"\n>>> {label}: finished. approved={snapshot.values.get('approved')} next={snapshot.next}"
        )
    elif p["type"] == "questions":
        print(f"\n>>> {label}: PAUSED for questions: {p['questions']}")
    else:
        print(
            f"\n>>> {label}: PAUSED for approval. total={p['estimated_total']} warnings={p['warnings']}"
        )


async def main():
    graph = build_graph(InMemorySaver())
    config = {"configurable": {"thread_id": "demo-1"}, "recursion_limit": 30}

    await graph.ainvoke({"user_text": "plan me a trip"}, config)
    show("1 start", await graph.aget_state(config))

    await graph.ainvoke(
        Command(
            resume="3 days in Jaipur and Udaipur, 30000 INR, 2 people, food and forts"
        ),
        config,
    )
    show("2 answered", await graph.aget_state(config))

    await graph.ainvoke(
        Command(resume={"approved": False, "feedback": "Make day 2 more relaxed"}),
        config,
    )
    show("3 edit requested", await graph.aget_state(config))

    await graph.ainvoke(Command(resume={"approved": True}), config)
    show("4 approved", await graph.aget_state(config))

    print("\nHistory (newest first):")
    async for snap in graph.aget_state_history(config):
        print("  step", snap.metadata.get("step"), "next", snap.next)


asyncio.run(main())
