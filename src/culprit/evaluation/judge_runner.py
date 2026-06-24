"""Judge Runner: drive the panel over a trajectory into an EvaluationResult.

For each step it selects the right component judge, samples it k times (once if
the backend is deterministic), aggregates with self-consistency, and — only on a
genuine low-confidence split — escalates to debate. It also runs the end-to-end
judge. Every judge call is guarded: a failure degrades to an ``unknown`` verdict
at confidence 0 rather than crashing the pipeline (NF2 reliability).
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from culprit.config import settings
from culprit.contracts import load_contracts
from culprit.contracts.loader import ContractStore
from culprit.evaluation.confidence import self_consistency
from culprit.evaluation.debate import run_debate
from culprit.evaluation.judges import (
    EndToEndJudge,
    component_judge_for,
    default_backend,
)
from culprit.evaluation.judges.base import RawJudgment
from culprit.schemas.evaluation import (
    ComponentVerdict,
    EndToEndVerdict,
    EvaluationResult,
    Verdict,
)
from culprit.schemas.trajectory import Step, Trajectory


class JudgeRunner:
    """Runs the two-level judge panel over a recorded trajectory."""

    def __init__(
        self,
        backend: Any | None = None,
        contracts: ContractStore | None = None,
        samples: int | None = None,
        tau: float | None = None,
        concurrency: int | None = None,
    ) -> None:
        self.backend = backend or default_backend()
        self.contracts = contracts or load_contracts()
        self.samples = samples or settings.judge_samples
        self.tau = tau if tau is not None else settings.tau
        self.concurrency = concurrency or settings.judge_concurrency

    def _k_samples(self, judge_fn: Callable[[float], RawJudgment]) -> list[RawJudgment]:
        """Sample a judge k times — concurrently, since the calls are independent.

        The deterministic backend takes the single-sample fast path (no network,
        nothing to parallelize).
        """
        if getattr(self.backend, "is_deterministic", False):
            return [judge_fn(0.0)]
        if self.samples == 1:
            return [judge_fn(0.7)]
        workers = min(self.samples, self.concurrency)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            return list(pool.map(lambda _: judge_fn(0.7), range(self.samples)))

    def evaluate_step(self, trajectory: Trajectory, step: Step) -> ComponentVerdict:
        """Evaluate a single step, with self-consistency and optional debate."""
        rubric = self.contracts.rubric_for(step.step_type)
        judge = component_judge_for(step.step_type, self.backend, rubric)
        if judge is None:
            return ComponentVerdict(
                step_id=step.step_id,
                step_type=step.step_type,
                verdict=Verdict.UNKNOWN,
                rationale="no judge registered for this step type",
            )

        try:
            samples = self._k_samples(lambda t: judge.judge_once(trajectory, step, t))
        except Exception as exc:
            return ComponentVerdict(
                step_id=step.step_id,
                step_type=step.step_type,
                verdict=Verdict.UNKNOWN,
                rationale=f"judge error: {exc}",
            )

        agg = self_consistency(samples)
        verdict = ComponentVerdict(
            step_id=step.step_id,
            step_type=step.step_type,
            verdict=agg.verdict,
            score=agg.score,
            confidence=agg.confidence,
            failure_category=agg.failure_category,
            rationale=agg.rationale,
            evidence=agg.evidence,
            samples=agg.samples,
        )

        if agg.disagreement and agg.confidence < self.tau:
            outcome = run_debate(
                judge.extract_context(trajectory, step), step.step_type, samples, self.backend
            )
            verdict.debated = True
            if outcome.resolved:
                verdict.verdict = outcome.verdict
                verdict.confidence = outcome.confidence
                verdict.failure_category = outcome.failure_category
                verdict.rationale = outcome.rationale
                if outcome.evidence:
                    verdict.evidence = outcome.evidence
            else:  # unresolved -> preserve the uncertainty signal for a human
                verdict.confidence = min(verdict.confidence, outcome.confidence)
                verdict.rationale = outcome.rationale or verdict.rationale

        return verdict

    def evaluate_end_to_end(self, trajectory: Trajectory) -> EndToEndVerdict:
        """Produce the task-level success verdict."""
        judge = EndToEndJudge(self.backend, self.contracts.task_success)
        try:
            samples = self._k_samples(lambda t: judge.judge_once(trajectory, t))
        except Exception as exc:
            return EndToEndVerdict(verdict=Verdict.UNKNOWN, rationale=f"judge error: {exc}")

        agg = self_consistency(samples)
        return EndToEndVerdict(
            verdict=agg.verdict,
            score=agg.score,
            confidence=agg.confidence,
            rationale=agg.rationale,
            evidence=agg.evidence,
        )

    def evaluate(self, trajectory: Trajectory) -> EvaluationResult:
        """Run both evaluation levels over the whole trajectory.

        Component judges and the end-to-end judge are mutually independent, so
        they run concurrently. Each one internally fans out its k samples too;
        the per-step pool is sized so the two levels of fan-out multiply to about
        ``judge_concurrency`` total in-flight calls rather than exploding.
        """
        steps = trajectory.ordered()

        if getattr(self.backend, "is_deterministic", False):
            components = [self.evaluate_step(trajectory, s) for s in steps]
            end_to_end = self.evaluate_end_to_end(trajectory)
            return EvaluationResult(
                run_id=trajectory.run_id,
                end_to_end=end_to_end,
                component_verdicts=components,
            )

        step_workers = max(1, self.concurrency // max(1, self.samples))
        with ThreadPoolExecutor(max_workers=step_workers + 1) as pool:
            comp_futures = [pool.submit(self.evaluate_step, trajectory, s) for s in steps]
            e2e_future = pool.submit(self.evaluate_end_to_end, trajectory)
            components = [f.result() for f in comp_futures]
            end_to_end = e2e_future.result()

        return EvaluationResult(
            run_id=trajectory.run_id,
            end_to_end=end_to_end,
            component_verdicts=components,
        )
