"""Meta-evaluation tab: how often Culprit attributes correctly.

Shows the headline metrics and per-component P/R/F1 from the meta-eval run, and
offers a button to (re)run it. Reads the structured metrics JSON written by the
meta-evaluator, keeping the UI decoupled from the scoring code.
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st


def render_meta_eval(output_dir: Path) -> None:
    """Render the meta-evaluation metrics, with a re-run control."""
    st.subheader("Judging the judges")

    if st.button("Run meta-evaluation"):
        with st.spinner("Injecting + fuzzing labeled faults and scoring attribution…"):
            from culprit.meta_eval import run_meta_eval

            run_meta_eval(output_dir=output_dir)
        st.rerun()

    metrics_path = output_dir / "meta_eval_metrics.json"
    if not metrics_path.exists():
        st.info("No meta-eval metrics yet. Run `python -m culprit.meta_eval` or click above.")
        return

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    cols = st.columns(3)
    cols[0].metric("Attribution accuracy", f"{metrics['attribution_accuracy']:.1%}")
    cols[1].metric("Step localization", f"{metrics['step_localization_accuracy']:.1%}")
    cols[2].metric("Confirmation rate", f"{metrics['confirmation_rate']:.1%}")
    st.caption(f"Evaluated over {metrics['n_cases']} labeled cases.")

    st.markdown("**Per-component precision / recall / F1**")
    st.table(
        [
            {
                "component": c["component"],
                "precision": c["precision"],
                "recall": c["recall"],
                "F1": c["f1"],
                "support": c["support"],
            }
            for c in metrics.get("per_category", [])
        ]
    )
