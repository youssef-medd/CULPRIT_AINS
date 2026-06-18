"""Evaluation verdict schemas — the output of the judge layer.

Two evaluation levels feed attribution: per-step ``ComponentVerdict``s (did
*this* step honor its contract?) and a single ``EndToEndVerdict`` (did the run
succeed at the task?). Both carry a self-consistency ``confidence`` so the
attribution engine can gate on it, and ``ComponentVerdict`` carries cited
``Evidence`` so the verdict is explainable rather than asserted.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from culprit.schemas.trajectory import StepType


class Verdict(StrEnum):
    """A judge's decision. ``UNKNOWN`` is the reliable-degradation outcome:

    a judge that times out or errors emits ``UNKNOWN`` at confidence 0 and is
    flagged for review rather than crashing the pipeline.
    """

    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


class Evidence(BaseModel):
    """One cited datum backing a verdict: a trajectory field and its expected
    vs. actual value. This is what makes a verdict auditable."""

    field: str
    expected: Any = None
    actual: Any = None
    note: str | None = None


class ComponentVerdict(BaseModel):
    """A per-step judgment of one component against its contract rubric."""

    step_id: str
    step_type: StepType
    verdict: Verdict = Verdict.UNKNOWN
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    failure_category: str | None = None
    rationale: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)

    # Bookkeeping for the self-consistency / debate layers.
    samples: int = Field(default=0, ge=0)
    debated: bool = False

    @property
    def is_failing(self) -> bool:
        """True when the judge decided this step failed its contract."""
        return self.verdict == Verdict.FAIL


class EndToEndVerdict(BaseModel):
    """The task-level success judgment for the whole run."""

    verdict: Verdict = Verdict.UNKNOWN
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)


class EvaluationResult(BaseModel):
    """The complete evaluation of one run: both levels, bundled for attribution."""

    run_id: str
    end_to_end: EndToEndVerdict = Field(default_factory=EndToEndVerdict)
    component_verdicts: list[ComponentVerdict] = Field(default_factory=list)

    def failing_components(self) -> list[ComponentVerdict]:
        """Component verdicts that failed, in trajectory order by step_id."""
        return [v for v in self.component_verdicts if v.is_failing]
