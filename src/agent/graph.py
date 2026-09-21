"""
LangGraph state machine definition for the Supplier Performance Agent.

The graph routes user intents to appropriate nodes, with explicit
interrupt nodes for human-in-the-loop approval of schema mappings,
scoring config, and alert thresholds.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph
from langchain_core.messages import AIMessage, HumanMessage

from src.agent.state import AgentState
from src.agent.nodes.intent_router import route_intent, classify_intent
from src.agent.nodes.schema_inference import handle_upload
from src.agent.nodes.scoring import handle_scorecard
from src.agent.nodes.alerting import handle_alerts
from src.agent.nodes.qa import handle_qa
from src.agent.nodes.approval_gate import handle_approval


def should_route(state: AgentState) -> str:
    """Conditional edge: route based on classified intent."""
    intent = state.get("current_intent")

    routes = {
        "upload": "schema_inference",
        "scorecard": "scoring",
        "alert": "alerting",
        "qa": "qa",
        "config": "qa",  # Config questions route through Q&A for now
        "compare": "qa",  # Comparison routes through Q&A (stub in Phase 4)
        "approve": "approval_gate",
        "help": "qa",
    }

    return routes.get(intent, "qa")


def needs_approval(state: AgentState) -> str:
    """Conditional edge: check if there's a pending approval."""
    if state.get("pending_approval"):
        return "wait_for_approval"
    return "end"


def build_graph() -> StateGraph:
    """
    Build the LangGraph state machine.

    Flow:
    1. Classify intent
    2. Route to appropriate handler node
    3. Handler may set pending_approval → interrupt for user input
    4. Resume on approval/rejection
    """
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("schema_inference", handle_upload)
    graph.add_node("scoring", handle_scorecard)
    graph.add_node("alerting", handle_alerts)
    graph.add_node("qa", handle_qa)
    graph.add_node("approval_gate", handle_approval)

    # Entry point
    graph.set_entry_point("classify_intent")

    # Conditional routing from intent classification
    graph.add_conditional_edges(
        "classify_intent",
        should_route,
        {
            "schema_inference": "schema_inference",
            "scoring": "scoring",
            "alerting": "alerting",
            "qa": "qa",
            "approval_gate": "approval_gate",
        },
    )

    # Each handler either ends or triggers an approval wait
    for node in ["schema_inference", "scoring", "alerting", "qa"]:
        graph.add_conditional_edges(
            node,
            needs_approval,
            {
                "wait_for_approval": END,  # Interrupt: return to user
                "end": END,
            },
        )

    graph.add_edge("approval_gate", END)

    return graph


def compile_graph():
    """Compile the graph into a runnable."""
    graph = build_graph()
    return graph.compile()


# Singleton compiled graph
agent_graph = compile_graph()
