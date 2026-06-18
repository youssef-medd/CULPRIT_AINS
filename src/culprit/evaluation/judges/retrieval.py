"""Retrieval component judge.

Focused context = the ticket the step saw plus the search result it produced
(filtered flag + retrieved tickets). That is all the judge needs to decide
whether the right, relevant context was fetched.
"""

from __future__ import annotations

from typing import Any

from culprit.evaluation.judges.base import BaseComponentJudge
from culprit.schemas.trajectory import Step, StepType, Trajectory


class RetrievalJudge(BaseComponentJudge):
    """Judges whether retrieval fetched relevant, properly-scoped context."""

    step_type = StepType.RETRIEVAL
    prompt_name = "retrieval"

    def extract_context(self, trajectory: Trajectory, step: Step) -> dict[str, Any]:
        result = step.result if isinstance(step.result, dict) else {}
        return {
            "ticket": step.context_snapshot.inputs.get("ticket", {}),
            "search_result": {k: v for k, v in result.items() if k != "results"},
            "retrieved": result.get("results", []),
        }
