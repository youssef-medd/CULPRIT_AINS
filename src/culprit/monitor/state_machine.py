"""The Shadow Monitor engine: run the compiled checkers over a trajectory.

Supports both arms of the design:

* **Online** — call ``observe(step)`` as each step is produced (the monitor runs
  in parallel with the live agent and returns alerts mid-flight).
* **Offline** — call ``run(trajectory)`` over a recorded trajectory to get the
  full set of structural violations for the attribution engine.

It only feeds steps to checkers and collects what they emit; all the property
logic lives in the checkers, so the engine stays a thin, deterministic driver.
"""

from __future__ import annotations

from culprit.contracts.loader import OrderingContract
from culprit.monitor.alerts import DivergenceAlert
from culprit.monitor.compiler import CapabilityResolver, Checker, compile_checkers
from culprit.schemas.trajectory import Step, Trajectory


class ShadowMonitor:
    """A runtime-verification monitor: a bank of checkers driven step by step."""

    def __init__(self, checkers: list[Checker]) -> None:
        self._checkers = checkers
        self.alerts: list[DivergenceAlert] = []

    def observe(self, step: Step) -> list[DivergenceAlert]:
        """Feed one step to every checker; return any alerts it triggered."""
        triggered = [alert for c in self._checkers if (alert := c.observe(step)) is not None]
        self.alerts.extend(triggered)
        return triggered

    def run(self, trajectory: Trajectory) -> list[DivergenceAlert]:
        """Observe every step of a recorded trajectory, in order."""
        for step in trajectory.ordered():
            self.observe(step)
        return self.alerts

    @property
    def diverged(self) -> bool:
        """True if any invariant has been violated so far."""
        return bool(self.alerts)

    def first_alert(self) -> DivergenceAlert | None:
        """The earliest violation by step index — a high-precision decisive hint."""
        if not self.alerts:
            return None
        return min(
            self.alerts,
            key=lambda a: (a.step_index if a.step_index is not None else 1 << 30),
        )


def build_monitor(
    ordering: OrderingContract | None = None,
    capability_resolver: CapabilityResolver | None = None,
) -> ShadowMonitor:
    """Build a monitor from an ordering contract (defaults to the loaded one)."""
    if ordering is None:
        from culprit.contracts import load_contracts

        ordering = load_contracts().ordering
    return ShadowMonitor(compile_checkers(ordering, capability_resolver))
