"""Generate demo data for the standalone dashboard (local, not committed).

Produces *real* attributions — faults are injected by the existing fault
injector and the verdicts are computed by the real attribution engine (heuristic
backend when no API key). This exists so the dashboard's headline view (decisive
red node, CRS, counterfactual proof, evidence) has honest failing runs to show,
since `culprit.run` over the clean synthetic tickets produces only passes.

Run from the repo root:

    python tools/gen_demo_data.py

Writes:
* data/outputs/<run_id>.json + .md   — the same verdict artifacts run.py writes
* ui/dashboard_data.js               — window.CULPRIT_DATA bundle the HTML reads
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from culprit.attribution import AttributionEngine
from culprit.config import REPO_ROOT, settings
from culprit.evaluation import JudgeRunner
from culprit.meta_eval.injector import inject
from culprit.monitor import build_monitor
from culprit.recorder import TrajectoryStore, record_run
from culprit.run import load_tickets
from culprit.verdict import VerdictRenderer

logger = logging.getLogger(__name__)

# fault_type -> tickets that make a coherent story for that fault
_FAULTS = {
    "retrieval_no_filter": ["JSM-101", "JSM-106"],   # networking
    "planning_wrong_team": ["JSM-103", "JSM-105"],   # email / software
    "tool_missing_arg": ["JSM-104", "JSM-102"],      # identity / printing
    "synthesis_inconsistent": ["JSM-105", "JSM-101"],  # software / networking
}
_PASS_TICKETS = ["JSM-101", "JSM-102", "JSM-103", "JSM-104", "JSM-106"]


def _tickets_by_id() -> dict[str, dict]:
    rows = load_tickets(REPO_ROOT / "data" / "synthetic" / "tickets.jsonl")
    return {t["id"]: t for t in rows}


def _total_ms(traj_dict: dict) -> float:
    return round(sum((s.get("latency_ms") or 0) for s in traj_dict.get("steps", [])), 1)


def _evaluate(trajectory, runner, engine, renderer):
    alerts = build_monitor().run(trajectory)
    evaluation = runner.evaluate(trajectory)
    attribution = engine.attribute(trajectory, evaluation, alerts=alerts)
    renderer.write(attribution)
    return attribution


def _record(run, ticket, attribution, label):
    td = run.model_dump(mode="json")
    return {
        "run_id": run.run_id,
        "ticket": ticket,
        "label": label.model_dump(mode="json") if label else None,
        "attribution": attribution.model_dump(mode="json"),
        "trajectory": td,
        "total_ms": _total_ms(td),
        "started_at": td.get("started_at"),
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    tickets = _tickets_by_id()
    store = TrajectoryStore()
    runner = JudgeRunner()
    engine = AttributionEngine()
    renderer = VerdictRenderer()

    runs: list[dict] = []

    # --- failing runs (each fault across a couple of tickets) ---
    for fault_type, ticket_ids in _FAULTS.items():
        for ticket_id in ticket_ids:
            good = record_run(tickets[ticket_id])
            case = inject(good, fault_type)
            traj = case.trajectory
            traj.run_id = f"demo_{fault_type}_{ticket_id}"
            store.save(traj)
            attribution = _evaluate(traj, runner, engine, renderer)
            runs.append(_record(traj, tickets[ticket_id], attribution, case.label))
            logger.info("  FAIL  %-34s  decisive=%s crs=%s confirmed=%s",
                        traj.run_id, attribution.decisive_step_type,
                        attribution.crs, attribution.confirmed)

    # --- passing runs (contrast) ---
    for ticket_id in _PASS_TICKETS:
        traj = record_run(tickets[ticket_id], run_id=f"demo_pass_{ticket_id}", store=store)
        attribution = _evaluate(traj, runner, engine, renderer)
        runs.append(_record(traj, tickets[ticket_id], attribution, None))
        logger.info("  PASS  %s", traj.run_id)

    # --- meta-eval metrics, if present ---
    metrics_path = settings.output_dir / "meta_eval_metrics.json"
    meta = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else None

    bundle = {
        "generated_at": datetime.now(UTC).isoformat(),
        "meta_eval": meta,
        "runs": runs,
    }

    out_js = REPO_ROOT / "ui" / "dashboard_data.js"
    out_js.write_text(
        "window.CULPRIT_DATA = " + json.dumps(bundle, indent=2, default=str) + ";",
        encoding="utf-8",
    )
    (REPO_ROOT / "ui" / "dashboard_data.json").write_text(
        json.dumps(bundle, indent=2, default=str), encoding="utf-8"
    )
    n_fail = sum(1 for r in runs if r["attribution"]["end_to_end_verdict"] == "fail")
    logger.info("\nWrote %d runs (%d fail) -> %s", len(runs), n_fail, out_js)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
