"""Tests for the top-level attribution algorithm."""

from culprit.attribution import attribute
from culprit.attribution.engine import _recommended_fix, _silent_failure, _why
from culprit.attribution.selector import Suspect
from culprit.meta_eval.injector import inject
from culprit.monitor import build_monitor
from culprit.schemas.attribution import Counterfactual, Repair
from culprit.schemas.evaluation import EndToEndVerdict, EvaluationResult, Verdict
from culprit.schemas.trajectory import RunStatus, StepType, Trajectory


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


def _eval(verdict: Verdict) -> EvaluationResult:
    return EvaluationResult(
        run_id="test",
        end_to_end=EndToEndVerdict(verdict=verdict),
        component_verdicts=[],
    )


def test_silent_failure_true_when_run_says_success_but_eval_says_fail():
    traj = Trajectory(run_id="test", steps=[], final_status=RunStatus.SUCCEEDED)
    assert _silent_failure(traj, _eval(Verdict.FAIL)) is True


def test_silent_failure_false_when_both_succeed():
    traj = Trajectory(run_id="test", steps=[], final_status=RunStatus.SUCCEEDED)
    assert _silent_failure(traj, _eval(Verdict.PASS)) is False


def test_silent_failure_false_when_both_fail():
    traj = Trajectory(run_id="test", steps=[], final_status=RunStatus.FAILED)
    assert _silent_failure(traj, _eval(Verdict.FAIL)) is False


def test_why_appends_silent_failure_note():
    traj = Trajectory(run_id="test", steps=[], final_status=RunStatus.SUCCEEDED)
    suspect = Suspect(
        step_id="s0", step_index=0, step_type=StepType.RETRIEVAL,
        confidence=0.9, rationale="Missing product_area filter."
    )
    explanation = _why(suspect, traj, _eval(Verdict.FAIL))
    assert "silent failure" in explanation.lower()
    assert "Missing product_area" in explanation


def test_why_uses_rationale_when_no_silent_failure():
    traj = Trajectory(run_id="test", steps=[], final_status=RunStatus.FAILED)
    suspect = Suspect(
        step_id="s0", step_index=0, step_type=StepType.RETRIEVAL,
        confidence=0.9, rationale="Explicit failure reason."
    )
    explanation = _why(suspect, traj, _eval(Verdict.FAIL))
    assert "Explicit failure" in explanation
    assert "silent failure" not in explanation.lower()


def test_recommended_fix_from_counterfactual():
    suspect = Suspect(
        step_id="s0", step_index=0, step_type=StepType.RETRIEVAL,
        confidence=0.9,
    )
    cf = Counterfactual(
        performed=True, confirms_attribution=True,
        repair=Repair(description="Populate product_area filter.", edits=[]),
    )
    fix = _recommended_fix(suspect, cf)
    assert fix == "Populate product_area filter."


def test_recommended_fix_from_hint_when_no_counterfactual():
    suspect = Suspect(
        step_id="s0", step_index=0, step_type=StepType.RETRIEVAL,
        confidence=0.9, failure_category="no_filter_applied",
    )
    cf = Counterfactual(performed=True, confirms_attribution=False)
    fix = _recommended_fix(suspect, cf)
    assert fix is not None
    assert "product_area" in fix


def test_recommended_fix_none_when_no_hint_and_unconfirmed():
    suspect = Suspect(
        step_id="s0", step_index=0, step_type=StepType.UNKNOWN,
        confidence=0.0, failure_category=None,
    )
    cf = Counterfactual(performed=True, confirms_attribution=False)
    assert _recommended_fix(suspect, cf) is None


def test_attribution_with_no_suspects_fallback(good_trajectory, runner):
    traj = Trajectory(
        run_id="no_suspects", steps=[], final_status=RunStatus.FAILED
    )
    eval_result = runner.evaluate(traj)
    a = attribute(traj, eval_result, alerts=[])
    assert a.end_to_end_verdict in (Verdict.FAIL, Verdict.UNKNOWN)
