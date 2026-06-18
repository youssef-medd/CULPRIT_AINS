"""Retrieve node: fetch similar prior tickets to ground the plan.

Scopes the search to the ticket's ``product_area`` (the correct behavior) and
records the tool call so the recorder and monitor can inspect it. Whatever this
node returns is what the planner trusts — so a bad retrieval here cascades.
"""

from __future__ import annotations

from typing import Any

from culprit.agent.state import AgentState
from culprit.agent.tools import search_tickets


def retrieve_node(state: AgentState) -> dict[str, Any]:
    """Search for relevant prior tickets and add them to the state."""
    ticket = state["ticket"]
    product_area = ticket.get("product_area")

    result = search_tickets(product_area=product_area, query=ticket.get("title", ""))

    tool_calls = list(state.get("tool_calls", []))
    tool_calls.append(
        {
            "tool": "search_tickets",
            "arguments": {"product_area": product_area, "query": ticket.get("title", "")},
            "result": result,
        }
    )

    return {"retrieved": result["results"], "tool_calls": tool_calls}
