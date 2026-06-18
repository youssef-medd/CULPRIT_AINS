"""Decisive-step selection (Who&When).

A suspect is a step that failed its contract with high confidence. Suspects come
from two layers: the semantic component judges and the deterministic Shadow
Monitor. A structural monitor alert is a cheap, high-precision signal, so it is
treated as a high-confidence suspect (and corroborates a judge verdict on the
same step). Suspects are ranked by step index; the *earliest* one is decisive,
which stops Culprit from blaming a downstream symptom of an upstream cause.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from culprit.monitor.alerts import DivergenceAlert
from culprit.schemas.evaluation import EvaluationResult, Evidence, Verdict
from culprit.schemas.trajectory import StepType, Trajectory

# Structural violations are deterministic and high-precision.
_MONITOR_CONFIDENCE = 0.95
_LATE = 1 << 30


@dataclass
class Suspect:
    """A step implicated in the failure, with its supporting signal."""

    step_id: str
    step_index: int
    step_type: StepType
    confidence: float
    failure_category: str | None = None
    rationale: str = ""
    evidence: list[Evidence] = field(default_factory=list)
    sources: tuple[str, ...] = ()


def _from_judges(trajectory: Trajectory, evaluation: EvaluationResult) -> dict[str, Suspect]:
    index = {s.step_id: s for s in trajectory.steps}
    suspects: dict[str, Suspect] = {}
    for verdict in evaluation.component_verdicts:
        if verdict.verdict != Verdict.FAIL:
            continue
        step = index.get(verdict.step_id)
        suspects[verdict.step_id] = Suspect(
            step_id=verdict.step_id,
            step_index=step.step_index if step else _LATE,
            step_type=verdict.step_type,
            confidence=verdict.confidence,
            failure_category=verdict.failure_category,
            rationale=verdict.rationale or "",
            evidence=list(verdict.evidence),
            sources=("judge",),
        )
    return suspects


def _merge_alerts(
    trajectory: Trajectory, alerts: list[DivergenceAlert], suspects: dict[str, Suspect]
) -> None:
    index = {s.step_id: s for s in trajectory.steps}
    for alert in alerts:
        if alert.step_id is None:
            continue
        step = index.get(alert.step_id)
        evidence = [Evidence(field=k, actual=v) for k, v in alert.evidence.items()]
        existing = suspects.get(alert.step_id)
        if existing is not None:
            suspects[alert.step_id] = replace(
                existing,
                confidence=max(existing.confidence, _MONITOR_CONFIDENCE),
                rationale=existing.rationale or alert.message,
                failure_category=existing.failure_category or alert.invariant_id,
                evidence=existing.evidence or evidence,
                sources=tuple(sorted({*existing.sources, "monitor"})),
            )
        else:
            suspects[alert.step_id] = Suspect(
                step_id=alert.step_id,
                step_index=step.step_index if step else (alert.step_index or _LATE),
                step_type=step.step_type if step else StepType.UNKNOWN,
                confidence=_MONITOR_CONFIDENCE,
                failure_category=alert.invariant_id,
                rationale=alert.message,
                evidence=evidence,
                sources=("monitor",),
            )


def select_suspects(
    trajectory: Trajectory,
    evaluation: EvaluationResult,
    alerts: list[DivergenceAlert] | None = None,
    tau: float = 0.7,
) -> list[Suspect]:
    """Return high-confidence suspects, earliest step first."""
    suspects = _from_judges(trajectory, evaluation)
    _merge_alerts(trajectory, alerts or [], suspects)
    high = [s for s in suspects.values() if s.confidence >= tau]
    high.sort(key=lambda s: s.step_index)
    return high


def earliest_failing(trajectory: Trajectory, evaluation: EvaluationResult) -> Suspect | None:
    """Earliest failing component regardless of confidence (E3 last resort)."""
    suspects = sorted(_from_judges(trajectory, evaluation).values(), key=lambda s: s.step_index)
    return suspects[0] if suspects else None
