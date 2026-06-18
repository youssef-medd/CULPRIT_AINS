"""The Attribution schema — Culprit's primary output.

Produced for *every* run (passing ones too). On failure it names the decisive
step, cites evidence, attaches a self-consistency confidence and a Causal
Responsibility Score, records whether counterfactual replay confirmed the
verdict, and gives a recommended fix. This is the proposed OTel-GenAI
"component-attribution event" the README documents as a protocol gap.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from culprit.schemas.evaluation import Evidence, Verdict
from culprit.schemas.trajectory import RunStatus, StepType


class RepairEdit(BaseModel):
    """A single-variable change tried during counterfactual replay."""

    field: str
    from_value: Any = None
    to_value: Any = None


class Repair(BaseModel):
    """A validated minimal repair: the smallest change that flipped the run to
    success, expressed as one or more single-variable edits plus prose."""

    description: str
    edits: list[RepairEdit] = Field(default_factory=list)

    @property
    def edit_size(self) -> int:
        """Number of variables changed (the minimality metric — smaller wins)."""
        return len(self.edits)


class Counterfactual(BaseModel):
    """The causal-confirmation record: did replaying from the suspect step with
    the proposed repair flip the outcome to success?"""

    performed: bool = False
    result: RunStatus | None = None
    confirms_attribution: bool = False
    minimal: bool = False  # True if a minimal edit flipped it; False if coarse fallback.
    repair: Repair | None = None


class Attribution(BaseModel):
    """The full verdict report for one run.

    Mirrors the JSON payload in the README. When ``end_to_end_verdict`` is
    ``PASS`` the failure fields stay empty; the report still ships (E4 requires
    a verdict for every run).
    """

    run_id: str
    end_to_end_verdict: Verdict = Verdict.UNKNOWN

    decisive_step_id: str | None = None
    decisive_step_type: StepType | None = None
    failure_category: str | None = None
    why: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)

    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    crs: float | None = Field(default=None, ge=0.0, le=1.0)

    counterfactual: Counterfactual = Field(default_factory=Counterfactual)
    confirmed: bool = False

    recommended_fix: str | None = None
    # Lower-ranked suspects, kept when attribution is unconfirmed.
    alternatives: list[str] = Field(default_factory=list)

    @property
    def is_pass(self) -> bool:
        """True for a passing run (no culprit to name)."""
        return self.end_to_end_verdict == Verdict.PASS
