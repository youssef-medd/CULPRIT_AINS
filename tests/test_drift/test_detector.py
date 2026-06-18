"""Tests for the drift detector."""

from culprit.drift import DriftDetector, psi
from culprit.meta_eval.injector import inject


def test_psi_identical_is_zero():
    dist = {"a": 5, "b": 5}
    assert psi(dist, dict(dist)) == 0.0


def test_psi_positive_on_shift():
    assert psi({"a": 10, "b": 0}, {"a": 0, "b": 10}) > 0.2


def test_stable_batch_no_drift(good_trajectory):
    det = DriftDetector()
    report = det.compare([good_trajectory], [good_trajectory])
    assert report.drifted is False


def test_misroute_batch_drifts_on_team(good_trajectory):
    drifted = inject(good_trajectory, "retrieval_no_filter").trajectory
    report = DriftDetector().compare([good_trajectory], [drifted])
    team = next(r for r in report.results if r.feature == "team")
    assert team.drifted is True
