"""The JSM triage agent as a LangGraph graph.

A linear 4-node graph — ``retrieve -> plan -> act -> synthesize`` — over the
shared ``AgentState``. An explicit node/edge graph is what makes step boundaries
first-class, which is exactly what the recorder and step-level attribution need.
The planner and summarizer are injected, defaulting to the deterministic ones so
the agent runs without an API key.
"""

from __future__ import annotations

from functools import partial
from typing import Any

from langgraph.graph import END, START, StateGraph

from culprit.agent.nodes import (
    Planner,
    Summarizer,
    act_node,
    default_planner,
    default_summarizer,
    plan_node,
    retrieve_node,
    synthesize_node,
)
from culprit.agent.state import AgentState, Ticket


def build_graph(
    planner: Planner | None = None,
    summarizer: Summarizer | None = None,
) -> Any:
    """Compile the triage graph with the given (or default) brains."""
    planner = planner or default_planner()
    summarizer = summarizer or default_summarizer()

    graph = StateGraph(AgentState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("plan", partial(plan_node, planner=planner))
    graph.add_node("act", act_node)
    graph.add_node("synthesize", partial(synthesize_node, summarizer=summarizer))

    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "plan")
    graph.add_edge("plan", "act")
    graph.add_edge("act", "synthesize")
    graph.add_edge("synthesize", END)

    return graph.compile()


def run_triage(
    ticket: dict[str, Any],
    planner: Planner | None = None,
    summarizer: Summarizer | None = None,
) -> AgentState:
    """Run the agent on a single ticket and return the final state."""
    normalized = Ticket.model_validate(ticket).model_dump()
    app = build_graph(planner=planner, summarizer=summarizer)
    initial: AgentState = {"ticket": normalized, "tool_calls": [], "jsm": {"comments": []}}
    result: AgentState = app.invoke(initial)
    return result
