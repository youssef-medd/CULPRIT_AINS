"""The subject under test: a JSM ticket-triage agent.

A deliberately simple 4-node LangGraph agent — it is what Culprit *evaluates*,
not the product. Public entrypoint::

    from culprit.agent import run_triage
    final_state = run_triage({"id": "JSM-1", "title": "VPN down", "product_area": "networking"})
"""

from culprit.agent.graph import build_graph, run_triage
from culprit.agent.state import AgentState, Plan, Ticket, ToolCall

__all__ = [
    "build_graph",
    "run_triage",
    "AgentState",
    "Ticket",
    "Plan",
    "ToolCall",
]
