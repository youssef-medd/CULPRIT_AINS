"""Mocked JSM tool: route the ticket to a team.

Writes to an in-memory JSM record instead of calling Jira, so runs are
deterministic and side-effect-free. Declares the ``route_team`` capability so
the Shadow Monitor can verify the agent used a tool actually capable of routing.
"""

from __future__ import annotations

from typing import Any

CAPABILITIES = frozenset({"route_team"})


def set_team(record: dict[str, Any], team: str) -> dict[str, Any]:
    """Set the assigned team on the mock JSM ``record`` and return the result."""
    if not team:
        return {"status": "error", "reason": "missing_required_argument", "field": "team"}
    record["team"] = team
    return {"status": "ok", "field": "team", "value": team}
