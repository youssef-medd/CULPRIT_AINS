"""Synthesize node: write the final triage summary.

The summary is grounded in what was *actually set* on the JSM record (not just
what was planned), so it stays consistent with the executed actions — the
property the synthesis rubric checks. Pluggable behind ``Summarizer`` mirroring
the planner: a deterministic template by default, an optional LLM summarizer.
"""

from __future__ import annotations

from typing import Any, Protocol

from culprit.agent.state import AgentState


class Summarizer(Protocol):
    """Anything that can turn the run's outcome into a summary string."""

    def summarize(
        self, ticket: dict[str, Any], record: dict[str, Any], plan: dict[str, Any]
    ) -> str: ...


class TemplateSummarizer:
    """Deterministic, grounded summary from the JSM record."""

    def summarize(
        self, ticket: dict[str, Any], record: dict[str, Any], plan: dict[str, Any]
    ) -> str:
        team = record.get("team") or "an unassigned team"
        priority = record.get("priority") or "an unset priority"
        title = ticket.get("title", "the ticket")
        rationale = plan.get("rationale", "")
        summary = f'Ticket "{title}" was routed to {team} at {priority} priority.'
        if rationale:
            summary += f" {rationale}"
        return summary


def default_summarizer() -> Summarizer:
    """Return the always-available deterministic summarizer."""
    return TemplateSummarizer()


def synthesize_node(state: AgentState, summarizer: Summarizer | None = None) -> dict[str, Any]:
    """Produce the final summary and the run's terminal status."""
    summarizer = summarizer or default_summarizer()
    record = state.get("jsm", {})
    summary = summarizer.summarize(state["ticket"], record, state.get("plan", {}))

    # No tool errored => the agent reports success. Whether the routing was
    # actually correct is for the judges to decide (the silent-failure gap).
    errored = any(c["result"].get("status") == "error" for c in state.get("tool_calls", []))
    status = "task_failed" if errored else "task_succeeded"

    return {"summary": summary, "status": status}
