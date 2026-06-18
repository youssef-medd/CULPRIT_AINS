"""LangGraph/LangChain callback handler that captures per-node timing.

LangGraph runs each node as a LangChain runnable and tags its callbacks with
``metadata["langgraph_node"]``. We use that to time each node (start -> end) and
expose the latencies, which the trajectory builder attaches to the steps. The
node deltas themselves are reconstructed from the final state, so this handler
stays small and robust to callback-shape differences across versions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler


class TrajectoryRecorder(BaseCallbackHandler):
    """Records the wall-clock latency of each graph node, in execution order."""

    def __init__(self) -> None:
        # Finalized node events: {node, step, started_at, ended_at, latency_ms}.
        self.node_events: list[dict[str, Any]] = []
        # In-flight starts keyed by the langchain run id.
        self._open: dict[UUID, dict[str, Any]] = {}

    def on_chain_start(
        self,
        serialized: dict[str, Any] | None,
        inputs: dict[str, Any],
        *,
        run_id: UUID,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        node = (metadata or {}).get("langgraph_node")
        if not node:  # the graph-level chain has no node name; ignore it
            return
        self._open[run_id] = {
            "node": node,
            "step": (metadata or {}).get("langgraph_step"),
            "started_at": datetime.now(timezone.utc),
        }

    def on_chain_end(self, outputs: Any, *, run_id: UUID, **kwargs: Any) -> None:
        event = self._open.pop(run_id, None)
        if event is None:
            return
        ended = datetime.now(timezone.utc)
        event["ended_at"] = ended
        event["latency_ms"] = (ended - event["started_at"]).total_seconds() * 1000.0
        self.node_events.append(event)

    def node_latency_ms(self) -> dict[str, float]:
        """Return {node_name: latency_ms} for every completed node."""
        return {e["node"]: e["latency_ms"] for e in self.node_events}
