"""Mocked JSM tools plus a capability registry.

Every tool declares the capabilities it provides. The registry is what lets the
Shadow Monitor (Phase 4) enforce the ``tool_capability`` invariants — e.g. that
routing was done by a tool actually capable of ``route_team`` — without the
monitor importing tool internals.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from culprit.agent.tools.add_comment import CAPABILITIES as ADD_COMMENT_CAPS
from culprit.agent.tools.add_comment import add_comment
from culprit.agent.tools.search_tickets import CAPABILITIES as SEARCH_CAPS
from culprit.agent.tools.search_tickets import search_tickets
from culprit.agent.tools.set_priority import CAPABILITIES as SET_PRIORITY_CAPS
from culprit.agent.tools.set_priority import set_priority
from culprit.agent.tools.set_team import CAPABILITIES as SET_TEAM_CAPS
from culprit.agent.tools.set_team import set_team


@dataclass(frozen=True)
class ToolSpec:
    """Metadata + callable for one mocked tool."""

    name: str
    capabilities: frozenset[str]
    fn: Callable[..., dict[str, Any]]

    def can(self, capability: str) -> bool:
        """True if this tool provides ``capability``."""
        return capability in self.capabilities


TOOLS: dict[str, ToolSpec] = {
    "search_tickets": ToolSpec("search_tickets", SEARCH_CAPS, search_tickets),
    "set_team": ToolSpec("set_team", SET_TEAM_CAPS, set_team),
    "set_priority": ToolSpec("set_priority", SET_PRIORITY_CAPS, set_priority),
    "add_comment": ToolSpec("add_comment", ADD_COMMENT_CAPS, add_comment),
}


def get_tool(name: str) -> ToolSpec | None:
    """Look up a tool spec by name."""
    return TOOLS.get(name)


def tool_can(name: str, capability: str) -> bool:
    """True if the named tool exists and provides ``capability``."""
    spec = TOOLS.get(name)
    return spec is not None and spec.can(capability)


__all__ = [
    "ToolSpec",
    "TOOLS",
    "get_tool",
    "tool_can",
    "search_tickets",
    "set_team",
    "set_priority",
    "add_comment",
]
