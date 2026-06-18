"""Verdict panel: the click-to-expand explainability surface.

Shows the attribution verdict, cited evidence, the counterfactual confirmation
with its validated repair, and the recommended fix. Operates on the attribution
JSON dict, so it stays decoupled from the core's pydantic types.
"""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_verdict(attribution: dict[str, Any]) -> None:
    """Render the human-readable verdict for one attribution."""
    if attribution.get("end_to_end_verdict") == "pass":
        st.success(f"✅ PASS — {attribution.get('why', 'Run succeeded at the task.')}")
        return

    st.error(
        f"❌ FAIL — decisive step `{attribution.get('decisive_step_id')}` "
        f"({attribution.get('decisive_step_type')})"
    )

    cols = st.columns(3)
    cols[0].metric("Confidence", f"{attribution.get('confidence', 0):.2f}")
    crs = attribution.get("crs")
    cols[1].metric("CRS", f"{crs:.2f}" if crs is not None else "n/a")
    cols[2].metric("Confirmed", "yes" if attribution.get("confirmed") else "no")

    st.markdown(f"**Failure category:** `{attribution.get('failure_category')}`")
    st.markdown(f"**Why:** {attribution.get('why')}")

    evidence = attribution.get("evidence") or []
    if evidence:
        with st.expander("Evidence", expanded=True):
            for e in evidence:
                st.markdown(
                    f"- `{e.get('field')}` — expected `{e.get('expected')}`, "
                    f"actual `{e.get('actual')}`"
                )

    cf = attribution.get("counterfactual") or {}
    with st.expander("Counterfactual confirmation", expanded=True):
        if cf.get("confirms_attribution"):
            kind = "minimal" if cf.get("minimal") else "coarse"
            st.write(f"Replay flipped the outcome to `{cf.get('result')}` via a {kind} repair.")
            repair = cf.get("repair") or {}
            if repair:
                st.markdown(f"**Validated repair:** {repair.get('description')}")
                for edit in repair.get("edits", []):
                    st.markdown(
                        f"- `{edit.get('field')}`: `{edit.get('from_value')}` → "
                        f"`{edit.get('to_value')}`"
                    )
        else:
            st.write("Not confirmed by replay; reported on correlational evidence.")

    st.info(f"**Recommended fix:** {attribution.get('recommended_fix') or 'n/a'}")

    alternatives = attribution.get("alternatives") or []
    if alternatives:
        st.caption("Alternative suspects: " + ", ".join(f"`{s}`" for s in alternatives))
