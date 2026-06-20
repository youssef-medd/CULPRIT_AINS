"""The attribution algorithm (E3): name the culprit, prove it, recommend a fix.

Implements the README's `attribute(...)`:

1. A passing run still gets a report (E4) — no culprit named.
2. Otherwise rank high-confidence suspects earliest-first (Who&When decisive step).
3. For each suspect, try to causally confirm it via counterfactual replay; the
   first one whose repair flips the outcome to success is the confirmed culprit.
4. If none confirm, blame the earliest suspect unconfirmed and list alternatives,
   so E3 always produces an attribution.
"""

from __future__ import annotations

from culprit.attribution.counterfactual import CounterfactualEngine
from culprit.attribution.crs import causal_responsibility
from culprit.attribution.selector import Suspect, earliest_failing, select_suspects
from culprit.config import settings
from culprit.monitor.alerts import DivergenceAlert
from culprit.schemas.attribution import Attribution, Counterfactual
from culprit.schemas.evaluation import EvaluationResult, Verdict
from culprit.schemas.trajectory import RunStatus, Trajectory

# Fallback fix suggestions keyed by failure category, used when no validated
# repair is available.
_FIX_HINTS: dict[str, str] = {
    "no_filter_applied": "Populate the product_area filter on the retrieval call.",
    "irrelevant_context_retrieved": "Scope retrieval to the ticket's product area and re-rank.",
    "insufficient_context_retrieved": "Broaden retrieval to return enough relevant tickets.",
    "wrong_team_selected": "Correct the routing rule for this product area.",
    "wrong_priority": "Re-derive priority from the ticket's severity signals.",
    "missing_required_argument": "Supply the missing tool argument before the call.",
    "inconsistent_with_actions": "Ground the summary in the team/priority actually set.",
}


def _silent_failure(trajectory: Trajectory, evaluation: EvaluationResult) -> bool:
    """True when the run reported success but the task verdict is failure."""
    return (
        trajectory.final_status == RunStatus.SUCCEEDED
        and evaluation.end_to_end.verdict == Verdict.FAIL
    )


def _why(suspect: Suspect, trajectory: Trajectory, evaluation: EvaluationResult) -> str:
    why = suspect.rationale or f"{suspect.step_type} failed its contract."
    if _silent_failure(trajectory, evaluation):
        why += " Every tool call returned ok, so no error fired — a silent failure."
    return why


def _recommended_fix(suspect: Suspect, counterfactual: Counterfactual) -> str | None:
    if counterfactual.confirms_attribution and counterfactual.repair:
        return counterfactual.repair.description
    if suspect.failure_category:
        return _FIX_HINTS.get(suspect.failure_category)
    return None


def _attribution_from(
    trajectory: Trajectory,
    evaluation: EvaluationResult,
    suspect: Suspect,
    counterfactual: Counterfactual,
    alternatives: list[Suspect],
) -> Attribution:
    confirmed = counterfactual.confirms_attribution
    crs = causal_responsibility(suspect.confidence, confirmed, counterfactual.minimal)
    return Attribution(
        run_id=trajectory.run_id,
        end_to_end_verdict=evaluation.end_to_end.verdict,
        decisive_step_id=suspect.step_id,
        decisive_step_type=suspect.step_type,
        failure_category=suspect.failure_category,
        why=_why(suspect, trajectory, evaluation),
        evidence=suspect.evidence,
        confidence=suspect.confidence,
        crs=crs,
        counterfactual=counterfactual,
        confirmed=confirmed,
        recommended_fix=_recommended_fix(suspect, counterfactual),
        alternatives=[s.step_id for s in alternatives],
    )


def attribute(
    trajectory: Trajectory,
    evaluation: EvaluationResult,
    alerts: list[DivergenceAlert] | None = None,
    tau: float | None = None,
    counterfactual_engine: CounterfactualEngine | None = None,
) -> Attribution:
    """Attribute a run's outcome to its decisive component (or report a pass)."""
    tau = settings.tau if tau is None else tau

    # 1) A passing run still gets a report.
    if evaluation.end_to_end.verdict == Verdict.PASS:
        return Attribution(
            run_id=trajectory.run_id,
            end_to_end_verdict=Verdict.PASS,
            confidence=evaluation.end_to_end.confidence,
            why="Run succeeded at the task; no decisive failure to attribute.",
        )

    # 2) Earliest high-confidence suspects.
    suspects = select_suspects(trajectory, evaluation, alerts, tau)

    if not suspects:
        # Last resort so E3 always attributes: earliest failing component, unconfirmed.
        fallback = earliest_failing(trajectory, evaluation)
        if fallback is None:
            return Attribution(
                run_id=trajectory.run_id,
                end_to_end_verdict=evaluation.end_to_end.verdict,
                why="Task failed but no component verdict isolated a cause.",
            )
        return _attribution_from(
            trajectory, evaluation, fallback, Counterfactual(performed=False), []
        )

    # 3) Confirm the earliest suspect that counterfactual replay validates.
    engine = counterfactual_engine or CounterfactualEngine()
    first_counterfactual: Counterfactual | None = None
    for i, suspect in enumerate(suspects):
        counterfactual = engine.confirm(trajectory, suspect)
        if first_counterfactual is None:
            first_counterfactual = counterfactual
        if counterfactual.confirms_attribution:
            return _attribution_from(
                trajectory, evaluation, suspect, counterfactual, suspects[:i] + suspects[i + 1 :]
            )

    # 4) None confirmed: blame the earliest suspect, list the rest as alternatives.
    return _attribution_from(
        trajectory,
        evaluation,
        suspects[0],
        first_counterfactual or Counterfactual(performed=True, confirms_attribution=False),
        suspects[1:],
    )


class AttributionEngine:
    """Convenience wrapper binding a counterfactual engine and tau."""

    def __init__(
        self, counterfactual_engine: CounterfactualEngine | None = None, tau: float | None = None
    ) -> None:
        self.counterfactual_engine = counterfactual_engine or CounterfactualEngine()
        self.tau = settings.tau if tau is None else tau

    def attribute(
        self,
        trajectory: Trajectory,
        evaluation: EvaluationResult,
        alerts: list[DivergenceAlert] | None = None,
    ) -> Attribution:
        return attribute(
            trajectory,
            evaluation,
            alerts=alerts,
            tau=self.tau,
            counterfactual_engine=self.counterfactual_engine,
        )
