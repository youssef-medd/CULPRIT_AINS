"""Synthesis component judge.

Focused context = the final summary text plus the JSM record and plan it should
be grounded in. The JSM record acts as the reference: the summary must assert
only the team/priority actually set, with nothing invented.
"""

from __future__ import annotations

from typing import Any

from culprit.evaluation.judges.base import BaseComponentJudge
from culprit.schemas.trajectory import Step, StepType, Trajectory


class SynthesisJudge(BaseComponentJudge):
    """Judges whether the summary is grounded in and consistent with the actions."""

    step_type = StepType.SYNTHESIS
    prompt_name = "synthesis"

    def extract_context(self, trajectory: Trajectory, step: Step) -> dict[str, Any]:
        return {
            "summary": step.result if isinstance(step.result, str) else "",
            "jsm": step.context_snapshot.inputs.get("jsm", {}),
            "plan": step.context_snapshot.inputs.get("plan", {}),
        }

    def reference(self, trajectory: Trajectory, step: Step) -> dict[str, Any] | None:
        return step.context_snapshot.inputs.get("jsm") or None
