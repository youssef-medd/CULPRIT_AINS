"""Self-consistency confidence (E6).

Each judge is sampled k times; the agreement among those samples becomes the
confidence. Majority verdict wins, confidence = fraction of samples that agree
with it, and the representative rationale/evidence is taken from the agreeing
samples. Genuine disagreement (a non-unanimous split) is flagged so the runner
can route it to debate before trusting the verdict.
"""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, Field

from culprit.evaluation.judges.base import RawJudgment
from culprit.schemas.evaluation import Evidence, Verdict


class ConfidenceResult(BaseModel):
    """The aggregated outcome of k self-consistency samples."""

    verdict: Verdict = Verdict.UNKNOWN
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    failure_category: str | None = None
    rationale: str = ""
    evidence: list[Evidence] = Field(default_factory=list)
    samples: int = 0
    disagreement: bool = False


def self_consistency(samples: list[RawJudgment]) -> ConfidenceResult:
    """Aggregate k judge samples into a single verdict + confidence."""
    n = len(samples)
    if n == 0:
        return ConfidenceResult()

    counts = Counter(s.verdict for s in samples)
    verdict, agree = counts.most_common(1)[0]
    agreeing = [s for s in samples if s.verdict == verdict]

    mean_score = sum(s.score for s in agreeing) / len(agreeing)
    # Representative explanation: the agreeing sample citing the most evidence.
    representative = max(agreeing, key=lambda s: (len(s.evidence), len(s.rationale)))

    failure_category = None
    if verdict == Verdict.FAIL:
        cats = Counter(s.failure_category for s in agreeing if s.failure_category)
        failure_category = cats.most_common(1)[0][0] if cats else representative.failure_category

    return ConfidenceResult(
        verdict=verdict,
        confidence=agree / n,
        score=mean_score,
        failure_category=failure_category,
        rationale=representative.rationale,
        evidence=representative.evidence,
        samples=n,
        disagreement=len(counts) > 1,
    )
