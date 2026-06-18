"""Deterministic fault injection: corrupt a known-good trajectory into a labeled
failing one.

The ground truth comes from the *injection*, not from any LLM oracle: each fault
records exactly which step it corrupted and into what failure category, so we can
later check whether Culprit attributes the failure back to that step/component.

Each fault produces a *coherent* corrupted trajectory — when retrieval is broken,
the downstream plan faithfully follows the bad context (so the cascade points at
retrieval, not planning), and so on. That coherence is what makes the localization
label honest.
"""

from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from culprit.schemas.trajectory import RunStatus, Step, StepStatus, StepType, Trajectory


class FaultLabel(BaseModel):
    """Ground truth for one injected fault."""

    fault_type: str
    step_id: str
    component: StepType
    failure_category: str


class InjectedCase(BaseModel):
    """A corrupted trajectory paired with its ground-truth label."""

    case_id: str
    trajectory: Trajectory
    label: FaultLabel


# A mix of off-topic resolved tickets used to simulate unfiltered retrieval.
_MIXED_RESULTS: list[dict[str, Any]] = [
    {"id": "T-2001", "title": "printer jam", "product_area": "printing", "team": "IT Hardware Support", "priority": "Low", "score": 0.6},
    {"id": "T-3001", "title": "email bounce", "product_area": "email", "team": "Messaging & Collaboration", "priority": "High", "score": 0.55},
]


# --------------------------------------------------------------------------- #
# Trajectory accessors / coherent mutators
# --------------------------------------------------------------------------- #
def _step_of(traj: Trajectory, step_type: StepType) -> Step | None:
    return next((s for s in traj.ordered() if s.step_type == step_type), None)


def _tool_steps(traj: Trajectory) -> list[Step]:
    return [s for s in traj.ordered() if s.step_type == StepType.TOOL_EXECUTION]


def _ticket_title(traj: Trajectory) -> str:
    r = _step_of(traj, StepType.RETRIEVAL)
    if r:
        return r.context_snapshot.inputs.get("ticket", {}).get("title", "the ticket")
    return "the ticket"


def _current_priority(traj: Trajectory) -> str:
    p = _step_of(traj, StepType.PLANNING)
    if p and isinstance(p.result, dict) and p.result.get("priority"):
        return p.result["priority"]
    return "Medium"


def _set_retrieved(traj: Trajectory, results: list[dict[str, Any]], filtered: bool) -> None:
    """Corrupt what retrieval returned, keeping the planner's view consistent."""
    r = _step_of(traj, StepType.RETRIEVAL)
    if r and r.action:
        if not filtered:
            r.action.arguments["product_area"] = None
        r.result = {
            "filtered": filtered,
            "product_area": r.action.arguments.get("product_area"),
            "count": len(results),
            "results": results,
        }
    p = _step_of(traj, StepType.PLANNING)
    if p:
        p.context_snapshot.inputs["retrieved"] = results


def _set_routing(traj: Trajectory, team: str, priority: str, summary: str | None = None) -> None:
    """Make the whole downstream reflect a (possibly wrong) team/priority."""
    plan = _step_of(traj, StepType.PLANNING)
    if plan and isinstance(plan.result, dict):
        plan.result["team"] = team
        plan.result["priority"] = priority
    plan_dict = plan.result if plan and isinstance(plan.result, dict) else {}

    for s in _tool_steps(traj):
        s.context_snapshot.inputs["plan"] = plan_dict
        if not s.action:
            continue
        if s.action.tool_name == "set_team":
            s.action.arguments["team"] = team
            s.result = {"status": "ok", "field": "team", "value": team}
            s.status = StepStatus.OK
        elif s.action.tool_name == "set_priority":
            s.action.arguments["priority"] = priority
            s.result = {"status": "ok", "field": "priority", "value": priority}
            s.status = StepStatus.OK

    syn = _step_of(traj, StepType.SYNTHESIS)
    if syn:
        record = syn.context_snapshot.inputs.setdefault("jsm", {})
        record["team"] = team
        record["priority"] = priority
        syn.context_snapshot.inputs["plan"] = plan_dict
        syn.result = summary or (
            f'Ticket "{_ticket_title(traj)}" was routed to {team} at {priority} priority.'
        )


# --------------------------------------------------------------------------- #
# Faults
# --------------------------------------------------------------------------- #
def inject_retrieval_no_filter(traj: Trajectory) -> tuple[Trajectory, FaultLabel]:
    """Retrieval runs unfiltered → mixed context → planner faithfully misroutes."""
    t = traj.model_copy(deep=True)
    plan = _step_of(t, StepType.PLANNING)
    correct_team = plan.result.get("team") if plan and isinstance(plan.result, dict) else None
    _set_retrieved(t, _MIXED_RESULTS, filtered=False)
    # Route to a team from the mixed context that genuinely differs from the
    # correct one, so the corrupted run actually misroutes (not a coincidental hit).
    teams = Counter(x["team"] for x in _MIXED_RESULTS)
    wrong_team = next(
        (tm for tm, _ in teams.most_common() if tm != correct_team), "Application Support"
    )
    _set_routing(t, wrong_team, _current_priority(t))
    r = _step_of(t, StepType.RETRIEVAL)
    return t, FaultLabel(
        fault_type="retrieval_no_filter",
        step_id=r.step_id,
        component=StepType.RETRIEVAL,
        failure_category="no_filter_applied",
    )


def inject_planning_wrong_team(traj: Trajectory) -> tuple[Trajectory, FaultLabel]:
    """Retrieval is fine but the plan ignores it and routes to the wrong team."""
    t = traj.model_copy(deep=True)
    plan = _step_of(t, StepType.PLANNING)
    good_team = plan.result.get("team") if plan and isinstance(plan.result, dict) else None
    wrong_team = "IT Hardware Support" if good_team != "IT Hardware Support" else "Application Support"
    _set_routing(t, wrong_team, _current_priority(t))
    return t, FaultLabel(
        fault_type="planning_wrong_team",
        step_id=plan.step_id,
        component=StepType.PLANNING,
        failure_category="plan_ignores_context",
    )


def inject_tool_missing_arg(traj: Trajectory) -> tuple[Trajectory, FaultLabel]:
    """The set_team call is made with an empty team → tool error, no routing."""
    t = traj.model_copy(deep=True)
    set_team_step = next(
        (s for s in _tool_steps(t) if s.action and s.action.tool_name == "set_team"), None
    )
    set_team_step.action.arguments["team"] = ""
    set_team_step.result = {"status": "error", "reason": "missing_required_argument", "field": "team"}
    set_team_step.status = StepStatus.ERROR

    syn = _step_of(t, StepType.SYNTHESIS)
    if syn:
        syn.context_snapshot.inputs.setdefault("jsm", {})["team"] = None
        syn.result = f"Triage incomplete: priority {_current_priority(t)} set but team unassigned."
    t.final_status = RunStatus.FAILED
    return t, FaultLabel(
        fault_type="tool_missing_arg",
        step_id=set_team_step.step_id,
        component=StepType.TOOL_EXECUTION,
        failure_category="missing_required_argument",
    )


def inject_synthesis_inconsistent(traj: Trajectory) -> tuple[Trajectory, FaultLabel]:
    """Routing is correct but the summary asserts a different team."""
    t = traj.model_copy(deep=True)
    syn = _step_of(t, StepType.SYNTHESIS)
    correct_team = syn.context_snapshot.inputs.get("jsm", {}).get("team")
    wrong_team = "IT Hardware Support" if correct_team != "IT Hardware Support" else "Application Support"
    syn.result = f'Ticket "{_ticket_title(t)}" was routed to {wrong_team}.'
    return t, FaultLabel(
        fault_type="synthesis_inconsistent",
        step_id=syn.step_id,
        component=StepType.SYNTHESIS,
        failure_category="inconsistent_with_actions",
    )


FAULTS: dict[str, Callable[[Trajectory], tuple[Trajectory, FaultLabel]]] = {
    "retrieval_no_filter": inject_retrieval_no_filter,
    "planning_wrong_team": inject_planning_wrong_team,
    "tool_missing_arg": inject_tool_missing_arg,
    "synthesis_inconsistent": inject_synthesis_inconsistent,
}


def inject(traj: Trajectory, fault_type: str) -> InjectedCase:
    """Apply a named fault to a good trajectory and return a labeled case."""
    corrupted, label = FAULTS[fault_type](traj)
    corrupted.run_id = f"inj_{fault_type}_{uuid.uuid4().hex[:6]}"
    return InjectedCase(case_id=corrupted.run_id, trajectory=corrupted, label=label)


def inject_all(traj: Trajectory) -> list[InjectedCase]:
    """Apply every known fault to a good trajectory."""
    return [inject(traj, fault_type) for fault_type in FAULTS]
