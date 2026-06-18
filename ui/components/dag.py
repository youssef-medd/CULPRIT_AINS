"""Interactive trajectory DAG: the trajectory as a directed graph.

Renders each step as a node (colored by type) with edges in execution order; the
decisive step is highlighted red. Uses Streamlit's built-in Graphviz rendering
so no extra graph dependency is required. This is a *decoupled* presentation
layer — it consumes the core's JSON (a trajectory dict + an attribution dict)
and knows nothing about the evaluation engine.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

_TYPE_COLOR = {
    "retrieval": "#4C9AFF",
    "planning": "#9F7AEA",
    "tool_execution": "#38B2AC",
    "synthesis": "#ED8936",
    "unknown": "#A0AEC0",
}
_DECISIVE_COLOR = "#E53E3E"


def _node_label(step: dict[str, Any]) -> str:
    label = f"{step['step_id']}\\n{step['step_type']}"
    action = step.get("action")
    if action:
        label += f"\\n{action['tool_name']}"
    return label


def build_dot(trajectory: dict[str, Any], decisive_step_id: str | None) -> str:
    """Build the Graphviz DOT source for a trajectory."""
    steps = sorted(trajectory.get("steps", []), key=lambda s: s["step_index"])
    lines = [
        "digraph trajectory {",
        "  rankdir=LR;",
        '  node [shape=box style="rounded,filled" fontname="Helvetica" fontsize=11];',
        '  edge [color="#718096"];',
    ]
    for step in steps:
        sid = step["step_id"]
        if sid == decisive_step_id:
            fill, font, pen = _DECISIVE_COLOR, "white", 3
        else:
            fill, font, pen = _TYPE_COLOR.get(step["step_type"], "#A0AEC0"), "black", 1
        lines.append(
            f'  "{sid}" [label="{_node_label(step)}" fillcolor="{fill}" '
            f'fontcolor="{font}" penwidth={pen}];'
        )
    for a, b in zip(steps, steps[1:]):
        lines.append(f'  "{a["step_id"]}" -> "{b["step_id"]}";')
    lines.append("}")
    return "\n".join(lines)


def render_dag(trajectory: dict[str, Any], attribution: dict[str, Any] | None = None) -> None:
    """Render the trajectory DAG with the decisive node highlighted."""
    decisive = (attribution or {}).get("decisive_step_id")
    st.graphviz_chart(build_dot(trajectory, decisive), use_container_width=True)
    if decisive:
        st.caption(f"🔴 Decisive step: {decisive}")
