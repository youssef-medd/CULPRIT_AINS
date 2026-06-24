"""End-to-end pipeline: run the agent and evaluate every run.

Wires the whole stack together for each ticket:

    record_run  ->  Shadow Monitor  ->  judges  ->  attribution  ->  verdict report

Structured verdicts (JSON) and human-readable reports (Markdown) are written to
the output directory; trajectories are persisted to the store. Run it as the
documented command::

    python -m culprit.run --tickets data/synthetic/tickets.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from culprit.attribution import AttributionEngine
from culprit.config import settings
from culprit.evaluation import JudgeRunner
from culprit.monitor import build_monitor
from culprit.recorder import TrajectoryStore, record_run
from culprit.verdict import VerdictRenderer, VerdictReport


def backend_banner() -> str:
    """A one-line statement of which evaluation backend is active.

    Makes the AI-vs-fallback mode explicit on every run, so the deterministic
    stand-in (used for CI/fixtures/reproducibility) is never mistaken for the
    real evaluation path — the LLM judges are the mechanism, not a feature.
    """
    if settings.nvidia_api_key:
        return (
            f"Backend: LLM judges - model={settings.judge_model} "
            f"via {settings.nvidia_base_url}  [AI evaluation path]"
        )
    return (
        "Backend: DETERMINISTIC FALLBACK - no NVIDIA_API_KEY set.\n"
        "  This is reproducibility mode (fixtures/CI/offline), NOT the AI evaluation\n"
        "  path. Set NVIDIA_API_KEY to run the real LLM judge panel."
    )


def load_tickets(path: Path) -> list[dict[str, Any]]:
    """Load tickets from a JSONL file (one ticket per line)."""
    tickets: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            tickets.append(json.loads(line))
    return tickets


def evaluate_ticket(
    ticket: dict[str, Any],
    runner: JudgeRunner,
    engine: AttributionEngine,
    renderer: VerdictRenderer,
    store: TrajectoryStore | None = None,
    output_dir: Path | None = None,
) -> VerdictReport:
    """Run the full pipeline for one ticket and return its rendered verdict."""
    trajectory = record_run(ticket, store=store)
    alerts = build_monitor().run(trajectory)
    evaluation = runner.evaluate(trajectory)
    attribution = engine.attribute(trajectory, evaluation, alerts=alerts)
    renderer.write(attribution, output_dir)
    return renderer.render(attribution)


def run_pipeline(
    tickets: list[dict[str, Any]],
    store: TrajectoryStore | None = None,
    output_dir: Path | None = None,
    backend: Any | None = None,
) -> list[VerdictReport]:
    """Run the pipeline over a list of tickets."""
    store = store or TrajectoryStore()
    runner = JudgeRunner(backend=backend)
    engine = AttributionEngine()
    renderer = VerdictRenderer()
    return [
        evaluate_ticket(t, runner, engine, renderer, store=store, output_dir=output_dir)
        for t in tickets
    ]


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for ``python -m culprit.run``."""
    parser = argparse.ArgumentParser(description="Run the Culprit evaluation pipeline.")
    parser.add_argument(
        "--tickets",
        type=Path,
        default=Path("data/synthetic/tickets.jsonl"),
        help="Path to a JSONL file of tickets to triage and evaluate.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=settings.output_dir,
        help="Directory for the structured verdicts and reports.",
    )
    args = parser.parse_args(argv)

    if not args.tickets.exists():
        print(f"error: tickets file not found: {args.tickets}", file=sys.stderr)
        return 1

    print(backend_banner(), file=sys.stderr)
    tickets = load_tickets(args.tickets)
    reports = run_pipeline(tickets, output_dir=args.output_dir)

    print(f"Evaluated {len(reports)} run(s). Verdicts written to {args.output_dir}\n")
    print(f"{'run_id':32}  {'verdict':5}  decisive / fix")
    print("-" * 88)
    for r in reports:
        a = r.attribution
        if a.is_pass:
            detail = "-"
        else:
            mark = "confirmed" if a.confirmed else "unconfirmed"
            detail = f"{a.decisive_step_id} {a.decisive_step_type} [{mark}] :: {a.recommended_fix}"
        print(f"{r.run_id:32}  {r.verdict:5}  {detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
