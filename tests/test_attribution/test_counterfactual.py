"""Tests for counterfactual confirmation."""

from culprit.attribution.counterfactual import CounterfactualEngine
from culprit.attribution.selector import select_suspects
from culprit.meta_eval.injector import inject
from culprit.monitor import build_monitor
from culprit.schemas.trajectory import RunStatus


def test_retrieval_fault_confirmed_minimal(good_trajectory, runner):
    case = inject(good_trajectory, "retrieval_no_filter")
    traj = case.trajectory
    evaluation = runner.evaluate(traj)
    alerts = build_monitor().run(traj)
    suspects = select_suspects(traj, evaluation, alerts, tau=0.7)
    decisive = suspects[0]

    cf = CounterfactualEngine(judge_runner=runner).confirm(traj, decisive)
    assert cf.performed is True
    assert cf.confirms_attribution is True
    assert cf.result == RunStatus.SUCCEEDED
    assert cf.repair is not None
