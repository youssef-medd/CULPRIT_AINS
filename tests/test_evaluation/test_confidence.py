"""Tests for self-consistency confidence aggregation."""

from culprit.evaluation.confidence import self_consistency
from culprit.evaluation.judges.base import RawJudgment
from culprit.schemas.evaluation import Verdict


def _j(verdict, score=0.8, cat=None):
    return RawJudgment(verdict=verdict, score=score, failure_category=cat, rationale="r")


def test_unanimous_full_confidence():
    result = self_consistency([_j(Verdict.PASS)] * 4)
    assert result.verdict == Verdict.PASS
    assert result.confidence == 1.0
    assert result.disagreement is False


def test_split_confidence_is_majority_fraction():
    samples = [_j(Verdict.FAIL, cat="x")] * 3 + [_j(Verdict.PASS)]
    result = self_consistency(samples)
    assert result.verdict == Verdict.FAIL
    assert result.confidence == 0.75
    assert result.disagreement is True
    assert result.failure_category == "x"


def test_empty_samples_unknown():
    result = self_consistency([])
    assert result.verdict == Verdict.UNKNOWN
    assert result.confidence == 0.0
