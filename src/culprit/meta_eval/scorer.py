"""Score Culprit's attribution against the labeled corpus (E7).

For each injected case we run the real attribution pipeline (monitor + judges +
counterfactual) and compare the decisive step/component against the ground-truth
label. Metrics reported:

* **attribution accuracy** — fraction with the right *component*.
* **step-localization accuracy** — fraction with the right *step* (benchmarked
  against the ~14.2% published SOTA the README cites).
* **per-category precision / recall / F1** over the components.
* **confirmation rate** — fraction confirmed by counterfactual replay.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from culprit.attribution import attribute
from culprit.evaluation import JudgeRunner
from culprit.meta_eval.injector import InjectedCase
from culprit.monitor import build_monitor
from culprit.schemas.trajectory import StepType


class CaseResult(BaseModel):
    """The scored outcome for a single injected case."""

    case_id: str
    fault_type: str
    gold_component: StepType
    gold_step: str
    pred_component: StepType | None = None
    pred_step: str | None = None
    confirmed: bool = False
    component_hit: bool = False
    step_hit: bool = False


class CategoryMetrics(BaseModel):
    """Precision/recall/F1 for one component class."""

    component: StepType
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    support: int = 0


class MetaEvalMetrics(BaseModel):
    """Aggregate metrics over the whole labeled corpus."""

    n_cases: int = 0
    attribution_accuracy: float = 0.0
    step_localization_accuracy: float = 0.0
    confirmation_rate: float = 0.0
    per_category: list[CategoryMetrics] = Field(default_factory=list)
    confusion: dict[str, dict[str, int]] = Field(default_factory=dict)


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return round(precision, 3), round(recall, 3), round(f1, 3)


class Scorer:
    """Runs attribution over labeled cases and aggregates metrics."""

    def __init__(self, runner: Any | None = None) -> None:
        self.runner = runner or JudgeRunner()

    def score_case(self, case: InjectedCase) -> CaseResult:
        """Attribute one case and compare to its ground-truth label."""
        trajectory = case.trajectory
        evaluation = self.runner.evaluate(trajectory)
        alerts = build_monitor().run(trajectory)
        attribution = attribute(trajectory, evaluation, alerts=alerts)

        pred_component = attribution.decisive_step_type
        pred_step = attribution.decisive_step_id
        return CaseResult(
            case_id=case.case_id,
            fault_type=case.label.fault_type,
            gold_component=case.label.component,
            gold_step=case.label.step_id,
            pred_component=pred_component,
            pred_step=pred_step,
            confirmed=attribution.confirmed,
            component_hit=pred_component == case.label.component,
            step_hit=pred_step == case.label.step_id,
        )

    def score(self, cases: list[InjectedCase]) -> tuple[MetaEvalMetrics, list[CaseResult]]:
        """Score every case and compute aggregate metrics."""
        results = [self.score_case(c) for c in cases]
        n = len(results)
        if n == 0:
            return MetaEvalMetrics(), results

        components = sorted({r.gold_component for r in results} | {
            r.pred_component for r in results if r.pred_component
        }, key=lambda c: c.value)

        per_category: list[CategoryMetrics] = []
        confusion: dict[str, dict[str, int]] = {c.value: {} for c in components}
        for r in results:
            gold = r.gold_component.value
            pred = r.pred_component.value if r.pred_component else "none"
            confusion.setdefault(gold, {})
            confusion[gold][pred] = confusion[gold].get(pred, 0) + 1

        for comp in components:
            tp = sum(1 for r in results if r.gold_component == comp and r.pred_component == comp)
            fp = sum(1 for r in results if r.gold_component != comp and r.pred_component == comp)
            fn = sum(1 for r in results if r.gold_component == comp and r.pred_component != comp)
            precision, recall, f1 = _prf(tp, fp, fn)
            per_category.append(
                CategoryMetrics(
                    component=comp,
                    precision=precision,
                    recall=recall,
                    f1=f1,
                    support=sum(1 for r in results if r.gold_component == comp),
                )
            )

        metrics = MetaEvalMetrics(
            n_cases=n,
            attribution_accuracy=round(sum(r.component_hit for r in results) / n, 3),
            step_localization_accuracy=round(sum(r.step_hit for r in results) / n, 3),
            confirmation_rate=round(sum(r.confirmed for r in results) / n, 3),
            per_category=per_category,
            confusion=confusion,
        )
        return metrics, results
