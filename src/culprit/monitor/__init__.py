"""Shadow Contract Monitor: deterministic runtime verification of ordering.

Compiles the contracts' ordering invariants into a state machine that runs
in parallel with the agent and fires a divergence alert the moment the
trajectory violates a structural rule — the cheap, online, high-precision arm
of drift detection that runs before any LLM judge::

    from culprit.monitor import build_monitor
    monitor = build_monitor()
    alerts = monitor.run(trajectory)        # offline over a recorded run
    # or, online:  for step in stream: monitor.observe(step)
"""

from culprit.monitor.alerts import AlertSeverity, DivergenceAlert
from culprit.monitor.compiler import (
    Checker,
    FieldAvailableChecker,
    PrecedesChecker,
    ToolCapabilityChecker,
    ToolOrderChecker,
    compile_checkers,
    default_capability_resolver,
)
from culprit.monitor.state_machine import ShadowMonitor, build_monitor

__all__ = [
    "AlertSeverity",
    "DivergenceAlert",
    "ShadowMonitor",
    "build_monitor",
    "compile_checkers",
    "default_capability_resolver",
    "Checker",
    "PrecedesChecker",
    "ToolOrderChecker",
    "ToolCapabilityChecker",
    "FieldAvailableChecker",
]
