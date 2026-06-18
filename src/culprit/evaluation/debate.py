"""Multi-agent debate for genuinely uncertain verdicts.

When the k self-consistency samples split, a short pass-vs-fail debate is put to
a Senior Judge before falling back to a human. The pass-leaning and fail-leaning
sample rationales are the two arguments; the Senior Judge adjudicates against the
focused context. Crucially this never erases the uncertainty signal: if the
Senior Judge can't decide (or no LLM is available to run it), the case still
escalates to a human.
"""

from __future__ import annotations

import random
from string import Template
from typing import Any

from pydantic import BaseModel, Field

from culprit.evaluation.judges.base import RawJudgment, load_prompt
from culprit.schemas.evaluation import Evidence, Verdict
from culprit.schemas.trajectory import StepType

# Confidence assigned to a verdict the Senior Judge resolved.
_RESOLVED_CONFIDENCE = 0.8


class DebateOutcome(BaseModel):
    """The result of adjudicating a disagreement."""

    verdict: Verdict = Verdict.UNKNOWN
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    failure_category: str | None = None
    rationale: str = ""
    evidence: list[Evidence] = Field(default_factory=list)
    resolved: bool = False
    escalate: bool = False


def _arguments(samples: list[RawJudgment], verdict: Verdict) -> str:
    """Join the rationales of samples that took a given stance."""
    rationales = [s.rationale for s in samples if s.verdict == verdict and s.rationale]
    return " ".join(rationales) if rationales else f"(no argument for {verdict.value})"


def run_debate(
    context: dict[str, Any],
    step_type: StepType,
    samples: list[RawJudgment],
    backend: Any,
    seed: int | None = None,
) -> DebateOutcome:
    """Adjudicate a split verdict; escalate to a human if it can't be resolved."""
    pass_arg = _arguments(samples, Verdict.PASS)
    fail_arg = _arguments(samples, Verdict.FAIL)
    n_pass = sum(1 for s in samples if s.verdict == Verdict.PASS)
    n_fail = sum(1 for s in samples if s.verdict == Verdict.FAIL)

    # No real adjudicator available -> keep the lean but escalate (never silently resolve).
    if getattr(backend, "is_deterministic", True) or not hasattr(backend, "judge_freeform"):
        return DebateOutcome(
            verdict=Verdict.PASS if n_pass >= n_fail else Verdict.FAIL,
            confidence=0.5,
            resolved=False,
            escalate=True,
            rationale="No LLM adjudicator available; escalating the split verdict to a human.",
        )

    rng = random.Random(seed)
    options = ["pass", "fail", "unknown"]
    rng.shuffle(options)
    import json

    prompt = Template(load_prompt("debate")).safe_substitute(
        step_type=step_type.value,
        context=json.dumps(context, default=str),
        pass_argument=pass_arg,
        fail_argument=fail_arg,
        verdict_options=" | ".join(options),
    )
    raw = backend.judge_freeform(prompt, temperature=0.3)

    if raw.verdict == Verdict.UNKNOWN:
        return DebateOutcome(
            verdict=Verdict.UNKNOWN,
            confidence=0.0,
            resolved=False,
            escalate=True,
            rationale=raw.rationale or "Senior judge could not decide; escalating to a human.",
        )

    return DebateOutcome(
        verdict=raw.verdict,
        confidence=_RESOLVED_CONFIDENCE,
        score=raw.score,
        failure_category=raw.failure_category,
        rationale=raw.rationale,
        evidence=raw.evidence,
        resolved=True,
        escalate=False,
    )
