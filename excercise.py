from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class AgentState(TypedDict):
    number1: int
    number2: int
    operation: str
    result: int


def addition_node(state: AgentState) -> AgentState:
    """This node adds two numbers"""
    state["result"] = state["number1"] + state["number2"]
    return state


def substract_node(state: AgentState) -> AgentState:
    """This node substract two numbers"""
    state["result"] = state["number1"] - state["number2"]
    return state


def router_node(state: AgentState) -> AgentState:
    """This node decides which node to call"""
    if state["operation"] == "+":
        return "addition_operation"
    elif state["operation"] == "-":
        return "substact_operation"


graph = StateGraph(AgentState)

graph.add_node("router", lambda state: state)
graph.add_node("addition_node", addition_node)
graph.add_node("substract_node", substract_node)

graph.add_edge(START, "router")
graph.add_conditional_edges(
    "router",
    router_node,
    {"addition_operation": "addition_node", "substact_operation": "substract_node"},
)
graph.add_edge("addition_node", END)
graph.add_edge("substract_node", END)

app = graph.compile()

print(app.get_graph().draw_mermaid())
