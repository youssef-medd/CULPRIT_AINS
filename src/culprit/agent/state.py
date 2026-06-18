"""The subject agent's state and the typed values that flow through the graph.

``AgentState`` is the LangGraph state dict: each node reads it and returns a
partial update that LangGraph merges. We keep the values plain (dicts / lists /
str) so the state is JSON-serializable and easy for the recorder to capture.
The pydantic models below are used *inside* nodes to build and validate those
values before they are dumped into the state.
"""

from __future__ import annotations

from typing import Any, TypedDict

from pydantic import BaseModel, Field


class Ticket(BaseModel):
    """An incoming JSM ticket to be triaged."""

    id: str
    title: str
    description: str = ""
    product_area: str | None = None
    reporter: str | None = None


class RetrievedTicket(BaseModel):
    """A resolved prior ticket returned by the retrieval tool."""

    id: str
    title: str
    product_area: str
    team: str
    priority: str
    score: float = Field(default=0.0, ge=0.0, le=1.0)


class Plan(BaseModel):
    """The planner's decision for how to triage the ticket."""

    team: str | None = None
    priority: str | None = None
    planned_actions: list[str] = Field(default_factory=list)
    rationale: str = ""


class ToolCall(BaseModel):
    """A record of one tool invocation (name, arguments, result)."""

    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)


class AgentState(TypedDict, total=False):
    """LangGraph state threaded through retrieve -> plan -> act -> synthesize."""

    ticket: dict[str, Any]
    retrieved: list[dict[str, Any]]
    plan: dict[str, Any]
    tool_calls: list[dict[str, Any]]
    jsm: dict[str, Any]  # mutable mock JSM record the action tools write to
    summary: str
    status: str
