"""Evaluation (E2 + E6): the semantic judging layer.

Per-step component judges and an end-to-end judge, run with self-consistency
confidence and debate escalation. The judges catch what the deterministic
Shadow Monitor cannot — irrelevant context, ungrounded summaries — using focused
context and (when a key is present) a real LLM, with a deterministic fallback::

    from culprit.evaluation import JudgeRunner
    result = JudgeRunner().evaluate(trajectory)
    result.end_to_end.verdict, result.failing_components()
"""

from culprit.evaluation.confidence import ConfidenceResult, self_consistency
from culprit.evaluation.debate import DebateOutcome, run_debate
from culprit.evaluation.judge_runner import JudgeRunner
from culprit.evaluation.judges import (
    EndToEndJudge,
    HeuristicJudgeBackend,
    LLMJudgeBackend,
    component_judge_for,
    default_backend,
)

__all__ = [
    "JudgeRunner",
    "self_consistency",
    "ConfidenceResult",
    "run_debate",
    "DebateOutcome",
    "EndToEndJudge",
    "component_judge_for",
    "default_backend",
    "LLMJudgeBackend",
    "HeuristicJudgeBackend",
]
