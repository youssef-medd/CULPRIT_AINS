"""Tests for the top-level attribution algorithm."""

from culprit.attribution import attribute
from culprit.meta_eval.injector import inject
from culprit.monitor import build_monitor
from culprit.schemas.evaluation import Verdict
from culprit.schemas.trajectory import StepType


def _attribute(traj, runner):
    return attribute(traj, runner.evaluate(traj), alerts=build_monitor().run(traj))


def test_pass_run_reports_pass(good_trajectory, runner):
    a = _attribute(good_trajectory, runner)
    assert a.end_to_end_verdict == Verdict.PASS
    assert a.decisive_step_id is None


def test_retrieval_fault_attributed_and_confirmed(good_trajectory, runner):
    case = inject(good_trajectory, "retrieval_no_filter")
    a = _attribute(case.trajectory, runner)
    assert a.decisive_step_type == StepType.RETRIEVAL
    assert a.confirmed is True
    assert a.recommended_fix
    assert a.crs is not None and a.crs > 0


def test_synthesis_fault_blames_synthesis(good_trajectory, runner):
    case = inject(good_trajectory, "synthesis_inconsistent")
    a = _attribute(case.trajectory, runner)
    assert a.decisive_step_type == StepType.SYNTHESIS
