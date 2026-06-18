"""Mocked JSM tool: add an internal comment to the ticket.

In-memory, side-effect-free. Declares the ``comment`` capability. Used by the
agent to leave a triage note; comments accumulate on the mock JSM record.
"""

from __future__ import annotations

from typing import Any

CAPABILITIES = frozenset({"comment"})


def add_comment(record: dict[str, Any], body: str) -> dict[str, Any]:
    """Append a comment to the mock JSM ``record`` and return the result."""
    if not body:
        return {"status": "error", "reason": "missing_required_argument", "field": "body"}
    comments = record.setdefault("comments", [])
    comments.append(body)
    return {"status": "ok", "field": "comments", "count": len(comments)}
