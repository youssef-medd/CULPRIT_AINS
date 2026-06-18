"""Planning component judge.

Focused context = the retrieved tickets the planner saw and the plan it produced
(team, priority, rationale). Judged on its own merits, so a plan that faithfully
follows poor retrieval can still pass locally — the cascade is resolved by the
earliest-decisive rule in attribution, not by over-failing this step.
"""

from __future__ import annotations

from typing import Any

from culprit.evaluation.judges.base import BaseComponentJudge
from culprit.schemas.trajectory import Step, StepType, Trajectory


class PlanningJudge(BaseComponentJudge):
    """Judges whether the plan follows from the ticket and retrieved context."""

    step_type = StepType.PLANNING
    prompt_name = "planning"

    def extract_context(self, trajectory: Trajectory, step: Step) -> dict[str, Any]:
        return {
            "retrieved": step.context_snapshot.inputs.get("retrieved", []),
            "plan": step.result if isinstance(step.result, dict) else {},
        }
