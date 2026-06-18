"""Drift tab: across-batch behavioral drift.

Lets the user split stored runs into a reference batch and a current batch and
computes PSI/KL drift per behavioral feature — the batch-timescale complement to
the within-run Shadow Monitor.
"""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_drift(run_ids: list[str], load_trajectory: Any) -> None:
    """Render the drift comparison UI over stored trajectories."""
    st.subheader("Behavioral drift across run batches")

    if len(run_ids) < 2:
        st.info("Need at least two stored runs to compare batches.")
        return

    reference_ids = st.multiselect("Reference batch", run_ids, default=run_ids[: len(run_ids) // 2])
    current_ids = st.multiselect("Current batch", run_ids, default=run_ids[len(run_ids) // 2 :])

    if not reference_ids or not current_ids:
        st.warning("Pick at least one run in each batch.")
        return

    from culprit.drift import DriftDetector

    reference = [t for rid in reference_ids if (t := load_trajectory(rid))]
    current = [t for rid in current_ids if (t := load_trajectory(rid))]
    report = DriftDetector().compare(reference, current)

    st.metric("Drift detected", "yes" if report.drifted else "no")
    st.table(
        [
            {
                "feature": r.feature,
                "PSI": r.psi,
                "KL": r.kl,
                "drifted": r.drifted,
            }
            for r in report.results
        ]
    )
    for r in report.results:
        if r.drifted:
            with st.expander(f"{r.feature} — distributions"):
                st.write({"reference": r.reference, "current": r.current})
