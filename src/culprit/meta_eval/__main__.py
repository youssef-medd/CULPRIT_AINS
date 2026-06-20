"""CLI for the meta-evaluator: ``python -m culprit.meta_eval``.

Injects + fuzzes a labeled fault corpus, scores Culprit's attribution over it,
writes the Fuzzing & Resilience Report, and prints the headline metrics.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from culprit.config import settings
from culprit.meta_eval import run_meta_eval
from culprit.run import load_tickets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Culprit meta-evaluation (judging the judges)."
    )
    parser.add_argument("--tickets", type=Path, default=None, help="JSONL tickets to fuzz from.")
    parser.add_argument("--seed", type=int, default=0, help="Fuzzing seed (reproducibility).")
    parser.add_argument(
        "--output-dir", type=Path, default=settings.output_dir, help="Report output dir."
    )
    args = parser.parse_args(argv)

    tickets = None
    if args.tickets is not None:
        if not args.tickets.exists():
            print(f"error: tickets file not found: {args.tickets}", file=sys.stderr)
            return 1
        tickets = load_tickets(args.tickets)

    report = run_meta_eval(tickets=tickets, seed=args.seed, output_dir=args.output_dir)
    m = report.metrics
    print(f"Meta-evaluation over {m.n_cases} labeled cases (report -> {args.output_dir})\n")
    print(f"  Attribution accuracy (component): {m.attribution_accuracy:.1%}")
    print(f"  Step-localization accuracy:       {m.step_localization_accuracy:.1%}")
    print(f"  Counterfactual confirmation rate: {m.confirmation_rate:.1%}\n")
    print(f"  {'component':16} {'P':>5} {'R':>5} {'F1':>5} {'support':>8}")
    for c in m.per_category:
        print(
            f"  {c.component.value:16} {c.precision:5.2f} {c.recall:5.2f} "
            f"{c.f1:5.2f} {c.support:8d}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
