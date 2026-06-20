"""Fuzzing & Resilience Report — the human-readable proof the evaluator works.

Renders the meta-evaluation metrics into a Markdown report (and writes the
structured metrics JSON alongside it), including the comparison against the
published step-localization SOTA the README cites (~14.2%).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from culprit.config import settings
from culprit.meta_eval.scorer import CaseResult, MetaEvalMetrics

# Published step-localization SOTA on Who&When (arXiv:2505.00212), for context.
_SOTA_STEP_LOCALIZATION = 0.142


class FuzzingReport(BaseModel):
    """The rendered meta-evaluation report plus its structured metrics."""

    metrics: MetaEvalMetrics
    results: list[CaseResult]
    text: str


def render_report(metrics: MetaEvalMetrics, results: list[CaseResult]) -> str:
    """Render the Markdown Fuzzing & Resilience Report."""
    lines: list[str] = [
        "# Culprit — Fuzzing & Resilience Report",
        "",
        f"Labeled cases evaluated: **{metrics.n_cases}**",
        "",
        "## Headline metrics",
        "",
        "| Metric | Score |",
        "|---|---|",
        f"| Attribution accuracy (component) | {metrics.attribution_accuracy:.1%} |",
        f"| Step-localization accuracy | {metrics.step_localization_accuracy:.1%} |",
        f"| Counterfactual confirmation rate | {metrics.confirmation_rate:.1%} |",
        "",
        (
            f"> Step-localization vs. published SOTA (~{_SOTA_STEP_LOCALIZATION:.1%} on Who&When): "
            f"**{metrics.step_localization_accuracy:.1%}** on this constrained domain — the "
            "scoping trade-off (one fixed agent, fixed step types) buying measurable accuracy."
        ),
        "",
        "## Per-component precision / recall / F1",
        "",
        "| Component | Precision | Recall | F1 | Support |",
        "|---|---|---|---|---|",
    ]
    for c in metrics.per_category:
        lines.append(
            f"| {c.component} | {c.precision:.2f} | {c.recall:.2f} | {c.f1:.2f} | {c.support} |"
        )

    lines += [
        "",
        "## Resilience by injected fault type",
        "",
        "| Fault type | Cases | Localized | Confirmed |",
        "|---|---|---|---|",
    ]
    fault_types = sorted({r.fault_type for r in results})
    for ft in fault_types:
        subset = [r for r in results if r.fault_type == ft]
        localized = sum(r.step_hit for r in subset)
        confirmed = sum(r.confirmed for r in subset)
        lines.append(
            f"| {ft} | {len(subset)} | {localized}/{len(subset)} | {confirmed}/{len(subset)} |"
        )

    misses = [r for r in results if not r.component_hit]
    lines += ["", "## Misattributions", ""]
    if misses:
        for r in misses:
            lines.append(
                f"- `{r.case_id}` ({r.fault_type}): expected {r.gold_component}, "
                f"got {r.pred_component}"
            )
    else:
        lines.append("_None — every injected fault was attributed to the correct component._")

    lines.append("")
    return "\n".join(lines)


def build_report(metrics: MetaEvalMetrics, results: list[CaseResult]) -> FuzzingReport:
    """Bundle metrics, per-case results, and the rendered text."""
    return FuzzingReport(metrics=metrics, results=results, text=render_report(metrics, results))


def write_report(report: FuzzingReport, output_dir: Path | None = None) -> dict[str, Path]:
    """Write the report Markdown and metrics JSON; return their paths."""
    out = output_dir or settings.output_dir
    out.mkdir(parents=True, exist_ok=True)
    md_path = out / "meta_eval_report.md"
    json_path = out / "meta_eval_metrics.json"
    md_path.write_text(report.text, encoding="utf-8")
    json_path.write_text(report.metrics.model_dump_json(indent=2), encoding="utf-8")
    return {"markdown": md_path, "json": json_path}
