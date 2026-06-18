"""Tool-execution component judge.

Focused context = the plan the action should honor, plus the actual call and its
result. Catches malformed/missing arguments, tool errors, and execution that
diverged from the plan.
"""

from __future__ import annotations

from typing import Any

from culprit.evaluation.judges.base import BaseComponentJudge
from culprit.schemas.trajectory import Step, StepType, Trajectory


class ToolExecutionJudge(BaseComponentJudge):
    """Judges whether a tool call was well-formed, capable, and faithful to the plan."""

    step_type = StepType.TOOL_EXECUTION
    prompt_name = "tool_execution"

    def extract_context(self, trajectory: Trajectory, step: Step) -> dict[str, Any]:
        return {
            "plan": step.context_snapshot.inputs.get("plan", {}),
            "action": step.action.model_dump() if step.action else None,
            "result": step.result,
        }
