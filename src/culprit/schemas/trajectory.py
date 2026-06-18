"""The Trajectory schema — Culprit's record of a single agent run.

Aligned with the OpenTelemetry GenAI semantic conventions: each ``Step`` is the
typed equivalent of an ``execute_tool`` / ``invoke_agent`` span, carrying the
reasoning, the action (tool + arguments), the result, latency, and status, plus
a per-step ``ContextSnapshot`` of what the step could see when it ran. The whole
``Trajectory`` is what the recorder emits and every downstream phase consumes.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class StepType(StrEnum):
    """The fixed step taxonomy of the JSM triage agent.

    Constraining the domain to these types is what lets the judges and the
    attribution engine localize a failure to one component.
    """

    RETRIEVAL = "retrieval"
    PLANNING = "planning"
    TOOL_EXECUTION = "tool_execution"
    SYNTHESIS = "synthesis"
    UNKNOWN = "unknown"


class StepStatus(StrEnum):
    """Execution outcome of a single step (not an evaluation verdict)."""

    OK = "ok"
    ERROR = "error"


class RunStatus(StrEnum):
    """Terminal status of the whole run as reported by the agent itself.

    Distinct from any judge verdict: a run can be ``SUCCEEDED`` here (no tool
    errored) yet still be judged a failure — that is exactly the silent-failure
    case Culprit exists to catch.
    """

    SUCCEEDED = "task_succeeded"
    FAILED = "task_failed"
    ERROR = "error"


class Action(BaseModel):
    """A tool invocation: the tool's name and the arguments passed to it."""

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ContextSnapshot(BaseModel):
    """What a step could see when it ran.

    Captured per step so a judge can be given *focused* context (just this
    step's inputs) rather than the whole trace — accuracy is anti-correlated
    with context length, so narrow context is a deliberate design choice.
    """

    inputs: dict[str, Any] = Field(default_factory=dict)
    available_fields: list[str] = Field(default_factory=list)


class Step(BaseModel):
    """One node of the trajectory: the typed equivalent of an OTel GenAI span."""

    step_id: str
    step_index: int = Field(ge=0)
    step_type: StepType = StepType.UNKNOWN
    span_name: str

    reasoning: str | None = None
    action: Action | None = None
    result: Any = None

    status: StepStatus = StepStatus.OK
    latency_ms: float | None = Field(default=None, ge=0.0)
    context_snapshot: ContextSnapshot = Field(default_factory=ContextSnapshot)

    started_at: datetime | None = None
    ended_at: datetime | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class Trajectory(BaseModel):
    """The full, ordered record of one agent run over one ticket."""

    run_id: str
    ticket_id: str | None = None
    steps: list[Step] = Field(default_factory=list)

    final_status: RunStatus = RunStatus.SUCCEEDED
    started_at: datetime | None = None
    ended_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def step_by_id(self, step_id: str) -> Step | None:
        """Return the step with ``step_id``, or ``None`` if absent."""
        return next((s for s in self.steps if s.step_id == step_id), None)

    def steps_of_type(self, step_type: StepType) -> list[Step]:
        """Return all steps of a given type, in trajectory order."""
        return [s for s in self.steps if s.step_type == step_type]

    def ordered(self) -> list[Step]:
        """Return steps sorted by ``step_index`` (defensive against insert order)."""
        return sorted(self.steps, key=lambda s: s.step_index)
