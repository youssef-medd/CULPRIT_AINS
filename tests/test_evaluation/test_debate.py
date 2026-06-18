"""Tests for debate escalation behavior."""

from culprit.evaluation.debate import run_debate
from culprit.evaluation.judges import HeuristicJudgeBackend
from culprit.evaluation.judges.base import RawJudgment
from culprit.schemas.evaluation import Verdict
from culprit.schemas.trajectory import StepType


def test_no_adjudicator_escalates():
    samples = [RawJudgment(verdict=Verdict.PASS), RawJudgment(verdict=Verdict.FAIL)]
    # Deterministic backend cannot adjudicate -> must escalate, never silently resolve.
    outcome = run_debate({}, StepType.RETRIEVAL, samples, HeuristicJudgeBackend())
    assert outcome.resolved is False
    assert outcome.escalate is True


def test_lean_follows_majority_when_unresolved():
    samples = [RawJudgment(verdict=Verdict.FAIL)] * 2 + [RawJudgment(verdict=Verdict.PASS)]
    outcome = run_debate({}, StepType.PLANNING, samples, HeuristicJudgeBackend())
    assert outcome.verdict == Verdict.FAIL
