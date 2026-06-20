"""Counterfactual confirmation via minimal repair.

Turns a correlational suspicion into a causal claim: re-run the agent from the
suspect step under a candidate correction and see whether the outcome flips to
success. The smallest single-variable change that flips it is reported as a
*validated* repair; if no minimal edit works, a coarse corrected-routing replay
is the fallback so E3 (attribution) is never left unconfirmed for lack of trying.

This is the highest-risk component by design and degrades gracefully: any replay
error is treated as "did not flip", never a crash.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from culprit.agent.nodes.plan import PRODUCT_AREA_TEAM, RuleBasedPlanner, infer_priority
from culprit.agent.nodes.synthesize import TemplateSummarizer
from culprit.agent.state import Plan
from culprit.attribution.selector import Suspect
from culprit.recorder import record_run
from culprit.schemas.attribution import Counterfactual, Repair, RepairEdit
from culprit.schemas.evaluation import Verdict
from culprit.schemas.trajectory import RunStatus, StepType, Trajectory

_PRODUCT_AREAS = list(PRODUCT_AREA_TEAM.keys())


# --------------------------------------------------------------------------- #
# Override brains used to inject a correction during replay
# --------------------------------------------------------------------------- #
class FixedPlanner:
    """Planner that forces a team/priority, deferring unset fields to the rules."""

    def __init__(self, team: str | None = None, priority: str | None = None) -> None:
        self._team = team
        self._priority = priority
        self._base = RuleBasedPlanner()

    def classify(self, ticket: dict[str, Any], retrieved: list[dict[str, Any]]) -> Plan:
        base = self._base.classify(ticket, retrieved)
        return Plan(
            team=self._team or base.team,
            priority=self._priority or base.priority,
            planned_actions=["set_team", "set_priority"],
            rationale="counterfactual override",
        )


class FixedSummarizer:
    """Summarizer that returns a fixed, grounded summary."""

    def __init__(self, summary: str) -> None:
        self._summary = summary

    def summarize(
        self, ticket: dict[str, Any], record: dict[str, Any], plan: dict[str, Any]
    ) -> str:
        return self._summary


# --------------------------------------------------------------------------- #
# Trajectory accessors
# --------------------------------------------------------------------------- #
def _ticket_from(trajectory: Trajectory) -> dict[str, Any]:
    for step in trajectory.ordered():
        ticket = step.context_snapshot.inputs.get("ticket")
        if ticket:
            return dict(ticket)
    return {"id": trajectory.ticket_id}


def _record_from(trajectory: Trajectory) -> dict[str, Any]:
    for step in trajectory.ordered():
        record = step.context_snapshot.inputs.get("jsm")
        if record:
            return dict(record)
    return {}


def _plan_from(trajectory: Trajectory) -> dict[str, Any]:
    for step in trajectory.steps_of_type(StepType.PLANNING):
        if isinstance(step.result, dict):
            return step.result
    return {}


@dataclass
class _Candidate:
    correction: dict[str, Any]
    repair: Repair


class CounterfactualEngine:
    """Searches for the smallest correction that flips the run to success."""

    def __init__(self, judge_runner: Any | None = None, max_edits: int = 4) -> None:
        if judge_runner is None:
            from culprit.evaluation.judge_runner import JudgeRunner

            judge_runner = JudgeRunner()
        self.runner = judge_runner
        self.max_edits = max_edits

    # --- replay primitive ---
    def _replay(
        self, trajectory: Trajectory, suspect: Suspect, correction: dict[str, Any]
    ) -> RunStatus:
        ticket = _ticket_from(trajectory)
        planner = None
        summarizer = None
        fixed_ticket = ticket

        if suspect.step_type == StepType.RETRIEVAL:
            fixed_ticket = {**ticket, **correction}
        elif suspect.step_type in (StepType.PLANNING, StepType.TOOL_EXECUTION):
            planner = FixedPlanner(correction.get("team"), correction.get("priority"))
        elif suspect.step_type == StepType.SYNTHESIS:
            summarizer = FixedSummarizer(correction.get("summary", ""))

        try:
            new_traj = record_run(fixed_ticket, planner=planner, summarizer=summarizer)
            e2e = self.runner.evaluate_end_to_end(new_traj)
        except Exception:
            return RunStatus.ERROR
        return RunStatus.SUCCEEDED if e2e.verdict == Verdict.PASS else RunStatus.FAILED

    # --- candidate proposal (smallest single-variable edits first) ---
    def _propose(self, trajectory: Trajectory, suspect: Suspect) -> list[_Candidate]:
        ticket = _ticket_from(trajectory)
        candidates: list[_Candidate] = []

        if suspect.step_type == StepType.RETRIEVAL:
            # The "from" value is what retrieval actually used (often null/wrong),
            # read off the decisive step itself, not the ticket.
            step = trajectory.step_by_id(suspect.step_id)
            current_area = (
                step.action.arguments.get("product_area") if step and step.action else None
            )
            areas: list[str] = []
            if ticket.get("product_area"):
                areas.append(ticket["product_area"])
            areas += [a for a in _PRODUCT_AREAS if a not in areas]
            for area in areas[: self.max_edits]:
                candidates.append(
                    _Candidate(
                        correction={"product_area": area},
                        repair=Repair(
                            description=(
                                f"Populate product_area='{area}' in the retrieval call "
                                "and add a relevance re-ranker."
                            ),
                            edits=[
                                RepairEdit(
                                    field="action.arguments.product_area",
                                    from_value=current_area,
                                    to_value=area,
                                )
                            ],
                        ),
                    )
                )
        elif suspect.step_type in (StepType.PLANNING, StepType.TOOL_EXECUTION):
            gold = PRODUCT_AREA_TEAM.get((ticket.get("product_area") or "").lower())
            if gold:
                candidates.append(
                    _Candidate(
                        correction={"team": gold},
                        repair=Repair(
                            description=f"Route to {gold} for the ticket's product area.",
                            edits=[RepairEdit(field="plan.team", to_value=gold)],
                        ),
                    )
                )
        elif suspect.step_type == StepType.SYNTHESIS:
            summary = TemplateSummarizer().summarize(
                ticket, _record_from(trajectory), _plan_from(trajectory)
            )
            candidates.append(
                _Candidate(
                    correction={"summary": summary},
                    repair=Repair(
                        description=(
                            "Regenerate the summary grounded strictly in the set "
                            "team/priority."
                        ),
                        edits=[RepairEdit(field="summary", to_value=summary)],
                    ),
                )
            )
        return candidates

    def _coarse(self, trajectory: Trajectory, suspect: Suspect) -> _Candidate | None:
        """Coarse corrected-routing replay used when no minimal edit flips it."""
        ticket = _ticket_from(trajectory)
        gold = PRODUCT_AREA_TEAM.get((ticket.get("product_area") or "").lower())
        if not gold:
            return None
        priority = infer_priority(ticket)
        return _Candidate(
            correction={"team": gold, "priority": priority},
            repair=Repair(
                description=f"Coarse correction: force routing to {gold} at {priority}.",
                edits=[
                    RepairEdit(field="plan.team", to_value=gold),
                    RepairEdit(field="plan.priority", to_value=priority),
                ],
            ),
        )

    # --- public API ---
    def confirm(self, trajectory: Trajectory, suspect: Suspect) -> Counterfactual:
        """Attempt to causally confirm the suspect by minimal, then coarse, replay."""
        candidates = sorted(self._propose(trajectory, suspect), key=lambda c: c.repair.edit_size)
        last_status = RunStatus.FAILED

        for candidate in candidates:
            status = self._replay(trajectory, suspect, candidate.correction)
            last_status = status
            if status == RunStatus.SUCCEEDED:
                return Counterfactual(
                    performed=True,
                    result=status,
                    confirms_attribution=True,
                    minimal=candidate.repair.edit_size <= 1,
                    repair=candidate.repair,
                )

        coarse = self._coarse(trajectory, suspect)
        if coarse is not None and suspect.step_type != StepType.SYNTHESIS:
            status = self._replay(
                trajectory, replace_step_type(suspect, StepType.PLANNING), coarse.correction
            )
            last_status = status
            if status == RunStatus.SUCCEEDED:
                return Counterfactual(
                    performed=True,
                    result=status,
                    confirms_attribution=True,
                    minimal=False,
                    repair=coarse.repair,
                )

        return Counterfactual(performed=True, result=last_status, confirms_attribution=False)


def replace_step_type(suspect: Suspect, step_type: StepType) -> Suspect:
    """Return a copy of the suspect with a different step type (for coarse replay)."""
    from dataclasses import replace

    return replace(suspect, step_type=step_type)
