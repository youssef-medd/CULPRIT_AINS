"""The divergence alert — the Shadow Monitor's output.

A ``DivergenceAlert`` is raised the moment a trajectory violates a structural
ordering invariant. It is the *online* protocol signal the README proposes
alongside the offline component-attribution event: cheap, high-precision, and
emitted before any LLM judge runs. Alerts are also a strong early signal for the
decisive-step selector in attribution.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AlertSeverity(StrEnum):
    """How hard a signal the alert is."""

    WARNING = "warning"
    VIOLATION = "violation"


class DivergenceAlert(BaseModel):
    """One structural-invariant violation, localized to the step that tripped it."""

    invariant_id: str
    kind: str  # the InvariantKind value the alert came from
    message: str
    severity: AlertSeverity = AlertSeverity.VIOLATION

    step_id: str | None = None
    step_index: int | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
