"""Tests for the two-level judge runner."""

from culprit.meta_eval.injector import inject
from culprit.schemas.evaluation import Verdict
from culprit.schemas.trajectory import StepType


def test_healthy_run_all_pass(good_trajectory, runner):
    result = runner.evaluate(good_trajectory)
    assert result.end_to_end.verdict == Verdict.PASS
    assert result.failing_components() == []


def test_retrieval_fault_fails_retrieval(good_trajectory, runner):
    case = inject(good_trajectory, "retrieval_no_filter")
    result = runner.evaluate(case.trajectory)
    failing = {v.step_type for v in result.failing_components()}
    assert StepType.RETRIEVAL in failing
    assert result.end_to_end.verdict == Verdict.FAIL


def test_confidence_present_on_verdicts(good_trajectory, runner):
    result = runner.evaluate(good_trajectory)
    assert all(0.0 <= v.confidence <= 1.0 for v in result.component_verdicts)
