"""Drift Monitor (E5, batch arm): behavioral distribution shift across run batches.

Complementary to the Shadow Monitor: that catches *within-run* structural
divergence online; this catches *across-batch* behavioral drift over time. It
compares the distribution of behavioral features (routing team, priority, run
status) between a reference batch and a current batch using the Population
Stability Index (PSI) and KL divergence — the standard ML-monitoring signals —
implemented in pure Python so the core carries no heavy numeric dependency.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Callable

from pydantic import BaseModel, Field

from culprit.schemas.trajectory import StepType, Trajectory

_EPS = 1e-6
# PSI rule of thumb: <0.1 stable, 0.1-0.2 moderate shift, >=0.2 significant.
_PSI_THRESHOLD = 0.2


# --------------------------------------------------------------------------- #
# Feature extractors (one behavioral value per trajectory)
# --------------------------------------------------------------------------- #
def _final_record(trajectory: Trajectory) -> dict:
    for step in trajectory.ordered():
        record = step.context_snapshot.inputs.get("jsm")
        if record:
            return record
    return {}


def team_of(trajectory: Trajectory) -> str:
    return _final_record(trajectory).get("team") or "(unassigned)"


def priority_of(trajectory: Trajectory) -> str:
    return _final_record(trajectory).get("priority") or "(unset)"


def status_of(trajectory: Trajectory) -> str:
    return trajectory.final_status.value


def tool_count_bucket(trajectory: Trajectory) -> str:
    n = len(trajectory.steps_of_type(StepType.TOOL_EXECUTION))
    return f"{n}_tools"


FEATURES: dict[str, Callable[[Trajectory], str]] = {
    "team": team_of,
    "priority": priority_of,
    "final_status": status_of,
    "tool_count": tool_count_bucket,
}


# --------------------------------------------------------------------------- #
# Divergence measures
# --------------------------------------------------------------------------- #
def _proportions(counts: dict[str, int], categories: set[str]) -> dict[str, float]:
    total = sum(counts.values()) or 1
    return {c: counts.get(c, 0) / total for c in categories}


def psi(expected: dict[str, int], actual: dict[str, int]) -> float:
    """Population Stability Index between two categorical distributions."""
    categories = set(expected) | set(actual)
    e = _proportions(expected, categories)
    a = _proportions(actual, categories)
    score = 0.0
    for c in categories:
        ev, av = max(e[c], _EPS), max(a[c], _EPS)
        score += (av - ev) * math.log(av / ev)
    return round(score, 4)


def kl_divergence(current: dict[str, int], reference: dict[str, int]) -> float:
    """KL(current || reference) between two categorical distributions."""
    categories = set(current) | set(reference)
    p = _proportions(current, categories)
    q = _proportions(reference, categories)
    score = 0.0
    for c in categories:
        if p[c] <= 0:
            continue
        score += p[c] * math.log(p[c] / max(q[c], _EPS))
    return round(score, 4)


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
class DriftResult(BaseModel):
    """Drift for one feature between reference and current batches."""

    feature: str
    psi: float
    kl: float
    drifted: bool
    reference: dict[str, int] = Field(default_factory=dict)
    current: dict[str, int] = Field(default_factory=dict)


class DriftReport(BaseModel):
    """Drift across all features between two batches."""

    n_reference: int
    n_current: int
    results: list[DriftResult] = Field(default_factory=list)

    @property
    def drifted(self) -> bool:
        return any(r.drifted for r in self.results)


class DriftDetector:
    """Compares behavioral feature distributions across two run batches."""

    def __init__(self, psi_threshold: float = _PSI_THRESHOLD) -> None:
        self.psi_threshold = psi_threshold

    def distribution(self, trajectories: list[Trajectory], feature: str) -> dict[str, int]:
        """Count the values of a feature across a batch of trajectories."""
        extractor = FEATURES[feature]
        return dict(Counter(extractor(t) for t in trajectories))

    def compare(
        self, reference: list[Trajectory], current: list[Trajectory]
    ) -> DriftReport:
        """Compute PSI/KL drift per feature between two batches."""
        results: list[DriftResult] = []
        for feature in FEATURES:
            ref = self.distribution(reference, feature)
            cur = self.distribution(current, feature)
            score = psi(ref, cur)
            results.append(
                DriftResult(
                    feature=feature,
                    psi=score,
                    kl=kl_divergence(cur, ref),
                    drifted=score >= self.psi_threshold,
                    reference=ref,
                    current=cur,
                )
            )
        return DriftReport(n_reference=len(reference), n_current=len(current), results=results)
