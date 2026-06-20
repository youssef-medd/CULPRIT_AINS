"""End-to-End judge: the task-level success verdict.

The second, distinct evaluation level. It reads the run's final outputs (team,
priority, summary) and judges them against the task-success contract. When the
ticket's product area is known it uses the expected team as a gold reference, so
a silent misroute (all tools ok, wrong team) is caught rather than passed.
"""

from __future__ import annotations

from typing import Any

from culprit.contracts.loader import TaskSuccessContract
from culprit.evaluation.judges.base import (
    EndToEndJudgeRequest,
    RawJudgment,
    load_prompt,
)
from culprit.schemas.trajectory import StepType, Trajectory


def _final_outputs(trajectory: Trajectory) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract (outputs, ticket) from a recorded trajectory."""
    ticket: dict[str, Any] = {}
    record: dict[str, Any] = {}
    summary: str | None = None

    for step in trajectory.ordered():
        inputs = step.context_snapshot.inputs
        if step.step_type == StepType.RETRIEVAL:
            ticket = inputs.get("ticket", ticket)
        if "jsm" in inputs:
            record = inputs["jsm"] or record
        if step.step_type == StepType.SYNTHESIS and isinstance(step.result, str):
            summary = step.result

    outputs = {
        "team": record.get("team"),
        "priority": record.get("priority"),
        "summary": summary,
    }
    return outputs, ticket


class EndToEndJudge:
    """Judges whether the whole run succeeded at the triage task."""

    prompt_name = "end_to_end"

    def __init__(self, backend: Any, task: TaskSuccessContract | None = None) -> None:
        self.backend = backend
        self.task = task

    def _expected_team(self, ticket: dict[str, Any]) -> dict[str, Any] | None:
        """Gold reference: the team a ticket's product area should route to."""
        from culprit.agent.nodes.plan import PRODUCT_AREA_TEAM

        area = (ticket.get("product_area") or "").lower()
        team = PRODUCT_AREA_TEAM.get(area)
        return {"expected_team": team} if team else None

    def build_request(self, trajectory: Trajectory) -> EndToEndJudgeRequest:
        outputs, ticket = _final_outputs(trajectory)
        return EndToEndJudgeRequest(
            run_id=trajectory.run_id,
            ticket=ticket,
            outputs=outputs,
            task=self.task,
            reference=self._expected_team(ticket),
            prompt_template=load_prompt(self.prompt_name),
        )

    def judge_once(self, trajectory: Trajectory, temperature: float = 0.0) -> RawJudgment:
        request = self.build_request(trajectory)
        result: RawJudgment = self.backend.judge_end_to_end(request, temperature)
        return result
