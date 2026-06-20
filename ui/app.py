"""Culprit dashboard — the interactive explainability surface (Streamlit).

A decoupled presentation layer over the core's outputs: it reads trajectories
from the store and attribution JSON from the output directory, and never touches
the evaluation engine's internals. Launch with::

    streamlit run ui/app.py

Three tabs: per-run trajectory DAG + verdict, meta-evaluation metrics, and
across-batch drift.
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
from components.dag import render_dag
from components.drift_tab import render_drift
from components.meta_eval_tab import render_meta_eval
from components.verdict_panel import render_verdict

from culprit.config import settings
from culprit.recorder import TrajectoryStore

st.set_page_config(page_title="Culprit", page_icon="🔎", layout="wide")

_CSS = Path(__file__).parent / "styles.css"
if _CSS.exists():
    st.markdown(f"<style>{_CSS.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

st.title("🔎 Culprit — component-level failure attribution")
st.caption("When an agent run fails, name the component, prove it, and recommend a fix.")


@st.cache_resource
def _store() -> TrajectoryStore:
    return TrajectoryStore()


def _load_attribution(run_id: str) -> dict | None:
    path = settings.output_dir / f"{run_id}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


store = _store()
run_ids = store.all_run_ids()

tab_runs, tab_meta, tab_drift = st.tabs(["Runs", "Meta-evaluation", "Drift"])

with tab_runs:
    if not run_ids:
        st.info(
            "No runs recorded yet. Run "
            "`python -m culprit.run --tickets data/synthetic/tickets.jsonl`."
        )
    else:
        run_id = st.sidebar.selectbox("Run", list(reversed(run_ids)))
        trajectory = store.get(run_id)
        attribution = _load_attribution(run_id)

        left, right = st.columns([3, 2])
        with left:
            st.subheader("Trajectory")
            if trajectory is not None:
                render_dag(trajectory.model_dump(), attribution)
        with right:
            st.subheader("Verdict")
            if attribution is not None:
                render_verdict(attribution)
            else:
                st.info("No verdict for this run yet — run the pipeline to generate one.")

with tab_meta:
    render_meta_eval(settings.output_dir)

with tab_drift:
    render_drift(run_ids, store.get)
