"""Tests for the meta-evaluation scorer."""

from culprit.meta_eval.injector import inject_all
from culprit.meta_eval.scorer import Scorer


def test_scores_injected_corpus_accurately(good_trajectory, runner):
    cases = inject_all(good_trajectory)
    metrics, results = Scorer(runner=runner).score(cases)

    assert metrics.n_cases == len(cases)
    # the heuristic stand-in localizes every coherent injected fault
    assert metrics.attribution_accuracy == 1.0
    assert metrics.step_localization_accuracy == 1.0
    assert all(r.component_hit and r.step_hit for r in results)


def test_per_category_metrics_present(good_trajectory, runner):
    metrics, _ = Scorer(runner=runner).score(inject_all(good_trajectory))
    assert metrics.per_category
    assert all(0.0 <= c.f1 <= 1.0 for c in metrics.per_category)
