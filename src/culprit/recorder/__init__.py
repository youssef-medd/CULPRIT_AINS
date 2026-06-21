"""Trajectory Recorder (E1): capture an agent run as a typed ``Trajectory``.

``record_run`` runs the subject agent with the timing callback attached, builds
the trajectory from the final state, tags each step's type, and (optionally)
persists it::

    from culprit.recorder import record_run, TrajectoryStore
    traj = record_run({"id": "JSM-1", "title": "VPN down", "product_area": "networking"},
                      store=TrajectoryStore())
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from culprit.agent.graph import build_graph
from culprit.agent.state import Ticket
from culprit.recorder.callback import TrajectoryRecorder
from culprit.recorder.store import TrajectoryStore
from culprit.recorder.trajectory_builder import build_trajectory, new_run_id
from culprit.schemas.trajectory import Trajectory
from culprit.tagger import tag_trajectory


@lru_cache(maxsize=2)
def _default_graph() -> Any:
    """Cached default compiled graph (no planner/summarizer overrides)."""
    return build_graph()


def _get_graph(planner: Any | None, summarizer: Any | None) -> Any:
    """Return a compiled graph, using the cached default when no overrides."""
    if planner is None and summarizer is None:
        return _default_graph()
    return build_graph(planner=planner, summarizer=summarizer)


def record_run(
    ticket: dict[str, Any],
    planner: Any | None = None,
    summarizer: Any | None = None,
    store: TrajectoryStore | None = None,
    run_id: str | None = None,
    use_llm_tagger: bool = False,
) -> Trajectory:
    """Run the agent on a ticket and return its captured, tagged trajectory."""
    normalized = Ticket.model_validate(ticket).model_dump()
    app = _get_graph(planner, summarizer)

    recorder = TrajectoryRecorder()
    initial = {"ticket": normalized, "tool_calls": [], "jsm": {"comments": []}}
    final_state = app.invoke(initial, config={"callbacks": [recorder]})

    trajectory = build_trajectory(
        run_id=run_id or new_run_id(),
        ticket=normalized,
        state=dict(final_state),
        node_latency_ms=recorder.node_latency_ms(),
    )
    tag_trajectory(trajectory, use_llm_fallback=use_llm_tagger)

    if store is not None:
        store.save(trajectory)
    return trajectory


__all__ = [
    "record_run",
    "TrajectoryRecorder",
    "TrajectoryStore",
    "build_trajectory",
    "new_run_id",
]
