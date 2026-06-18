"""Act node: execute the planned actions via the mocked JSM tools.

Calls ``set_team`` then ``set_priority`` (the order the ordering invariant
expects) against the in-memory JSM record, recording each tool call. A planned
value of ``None`` is passed straight through so the tool surfaces it as a
missing-argument error rather than being silently skipped — the recorder needs
to see the real failure.
"""

from __future__ import annotations

from typing import Any

from culprit.agent.state import AgentState
from culprit.agent.tools import set_priority, set_team


def act_node(state: AgentState) -> dict[str, Any]:
    """Apply the plan's team and priority to the mock JSM record."""
    plan = state.get("plan", {})
    record: dict[str, Any] = dict(state.get("jsm", {"comments": []}))
    tool_calls = list(state.get("tool_calls", []))

    team = plan.get("team")
    res_team = set_team(record, team)
    tool_calls.append({"tool": "set_team", "arguments": {"team": team}, "result": res_team})

    priority = plan.get("priority")
    res_priority = set_priority(record, priority)
    tool_calls.append(
        {"tool": "set_priority", "arguments": {"priority": priority}, "result": res_priority}
    )

    return {"jsm": record, "tool_calls": tool_calls}
