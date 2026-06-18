"""Drift Monitor (E5): across-batch behavioral drift via PSI / KL.

The batch-timescale counterpart to the within-run Shadow Monitor::

    from culprit.drift import DriftDetector
    report = DriftDetector().compare(reference_batch, current_batch)
    report.drifted  # True if any feature shifted significantly
"""

from culprit.drift.detector import (
    DriftDetector,
    DriftReport,
    DriftResult,
    kl_divergence,
    psi,
)

__all__ = [
    "DriftDetector",
    "DriftReport",
    "DriftResult",
    "psi",
    "kl_divergence",
]
