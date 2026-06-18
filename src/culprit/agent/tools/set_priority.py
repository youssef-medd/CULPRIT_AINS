"""Mocked JSM tool: set the ticket's priority.

In-memory, side-effect-free. Declares the ``set_priority`` capability and
validates against the allowed levels so a malformed value surfaces as a tool
error the recorder can capture.
"""

from __future__ import annotations

from typing import Any

CAPABILITIES = frozenset({"set_priority"})

ALLOWED_PRIORITIES = ("Low", "Medium", "High", "Critical")


def set_priority(record: dict[str, Any], priority: str) -> dict[str, Any]:
    """Set the priority on the mock JSM ``record`` and return the result."""
    if not priority:
        return {"status": "error", "reason": "missing_required_argument", "field": "priority"}
    if priority not in ALLOWED_PRIORITIES:
        return {
            "status": "error",
            "reason": "malformed_arguments",
            "field": "priority",
            "value": priority,
            "allowed": list(ALLOWED_PRIORITIES),
        }
    record["priority"] = priority
    return {"status": "ok", "field": "priority", "value": priority}
