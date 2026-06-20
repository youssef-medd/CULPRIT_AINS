"""Assemble a captured agent run into a typed ``Trajectory``.

Expands the final agent state into ordered, per-action steps so attribution can
localize to a single action:

    step_00 retrieval        (the search_tickets call)
    step_01 planning         (the plan node's decision)
    step_02 tool_execution   (set_team)
    step_03 tool_execution   (set_priority)
    step_04 synthesis        (the final summary)

Step *types* are intentionally left ``UNKNOWN`` here — assigning them is the Step
Tagger's job, keeping capture (structure) and tagging (semantics) separate.
Node-level latency from the callback is attached when available.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from culprit.schemas.trajectory import (
    Action,
    ContextSnapshot,
    RunStatus,
    Step,
    StepStatus,
    Trajectory,
)

_ACTION_TOOLS = ("set_team", "set_priority", "add_comment")


def new_run_id() -> str:
    """Generate a readable, unique run id like ``run_20260618_143012_a1b2``."""
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return f"run_{stamp}_{uuid.uuid4().hex[:4]}"


def _status_of(result: dict[str, Any] | None) -> StepStatus:
    """Map a tool result dict to a step status."""
    if isinstance(result, dict) and result.get("status") == "error":
        return StepStatus.ERROR
    return StepStatus.OK


def build_trajectory(
    run_id: str,
    ticket: dict[str, Any],
    state: dict[str, Any],
    node_latency_ms: dict[str, float] | None = None,
) -> Trajectory:
    """Build a ``Trajectory`` from the agent's final ``state``."""
    latency = node_latency_ms or {}
    tool_calls: list[dict[str, Any]] = state.get("tool_calls", [])
    steps: list[Step] = []
    idx = 0

    # --- retrieval ---
    search = next((c for c in tool_calls if c["tool"] == "search_tickets"), None)
    if search is not None:
        steps.append(
            Step(
                step_id=f"step_{idx:02d}",
                step_index=idx,
                span_name="retrieve",
                action=Action(tool_name="search_tickets", arguments=search["arguments"]),
                result=search["result"],
                status=_status_of(search["result"]),
                latency_ms=latency.get("retrieve"),
                context_snapshot=ContextSnapshot(
                    inputs={"ticket": ticket},
                    available_fields=sorted(ticket.keys()),
                ),
            )
        )
        idx += 1

    # --- planning ---
    plan = state.get("plan")
    if plan is not None:
        steps.append(
            Step(
                step_id=f"step_{idx:02d}",
                step_index=idx,
                span_name="plan",
                reasoning=plan.get("rationale"),
                result=plan,
                latency_ms=latency.get("plan"),
                context_snapshot=ContextSnapshot(
                    inputs={"retrieved": state.get("retrieved", [])},
                    available_fields=["ticket", "retrieved"],
                ),
            )
        )
        idx += 1

    # --- tool execution (one step per action call) ---
    for call in (c for c in tool_calls if c["tool"] in _ACTION_TOOLS):
        steps.append(
            Step(
                step_id=f"step_{idx:02d}",
                step_index=idx,
                span_name="act",
                action=Action(tool_name=call["tool"], arguments=call["arguments"]),
                result=call["result"],
                status=_status_of(call["result"]),
                context_snapshot=ContextSnapshot(
                    inputs={"plan": plan},
                    available_fields=["plan"],
                ),
                attributes={"node": "act"},
            )
        )
        idx += 1

    # --- synthesis ---
    summary = state.get("summary")
    if summary is not None:
        steps.append(
            Step(
                step_id=f"step_{idx:02d}",
                step_index=idx,
                span_name="synthesize",
                result=summary,
                latency_ms=latency.get("synthesize"),
                context_snapshot=ContextSnapshot(
                    inputs={"jsm": state.get("jsm", {}), "plan": plan},
                    available_fields=["jsm", "plan"],
                ),
            )
        )
        idx += 1

    raw_status = state.get("status", "task_succeeded")
    try:
        final_status = RunStatus(raw_status)
    except ValueError:
        final_status = RunStatus.SUCCEEDED

    return Trajectory(
        run_id=run_id,
        ticket_id=ticket.get("id"),
        steps=steps,
        final_status=final_status,
        metadata={"node_count": len(latency)},
    )
