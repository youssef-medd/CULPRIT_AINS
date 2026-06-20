"""Meta-Evaluator (E7): judging the judges.

Manufactures ground truth by injecting + fuzzing labeled faults, runs Culprit's
attribution over the corpus, and measures how often it attributes correctly::

    from culprit.meta_eval import run_meta_eval
    report = run_meta_eval()
    report.metrics.attribution_accuracy, report.metrics.step_localization_accuracy
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from culprit.config import REPO_ROOT
from culprit.meta_eval.injector import FAULTS, FaultLabel, InjectedCase, inject, inject_all
from culprit.meta_eval.mutation_engine import MutationEngine
from culprit.meta_eval.report import FuzzingReport, build_report, write_report
from culprit.meta_eval.scorer import CaseResult, MetaEvalMetrics, Scorer

_DEFAULT_TICKETS = REPO_ROOT / "data" / "synthetic" / "tickets.jsonl"


def run_meta_eval(
    tickets: list[dict[str, Any]] | None = None,
    seed: int = 0,
    output_dir: Path | None = None,
    write: bool = True,
) -> FuzzingReport:
    """Fuzz a labeled corpus, score attribution over it, and build the report."""
    if tickets is None:
        from culprit.run import load_tickets

        tickets = load_tickets(_DEFAULT_TICKETS)

    cases = MutationEngine(seed=seed).fuzz_tickets(tickets)
    metrics, results = Scorer().score(cases)
    report = build_report(metrics, results)
    if write:
        write_report(report, output_dir)
    return report


__all__ = [
    "run_meta_eval",
    "FAULTS",
    "FaultLabel",
    "InjectedCase",
    "inject",
    "inject_all",
    "MutationEngine",
    "Scorer",
    "MetaEvalMetrics",
    "CaseResult",
    "FuzzingReport",
    "build_report",
    "write_report",
]
