"""Shared, OTel-GenAI-aligned data types used across every subsystem.

These are the contract between phases: the recorder produces a ``Trajectory``,
the judges produce ``ComponentVerdict``/``EndToEndVerdict``, and the attribution
engine produces an ``Attribution``. Keeping them in one place means no subsystem
depends on another's internals — only on these types.
"""

from culprit.schemas.attribution import (
    Attribution,
    Counterfactual,
    Repair,
    RepairEdit,
)
from culprit.schemas.evaluation import (
    ComponentVerdict,
    EndToEndVerdict,
    EvaluationResult,
    Evidence,
    Verdict,
)
from culprit.schemas.trajectory import (
    Action,
    ContextSnapshot,
    RunStatus,
    Step,
    StepStatus,
    StepType,
    Trajectory,
)

__all__ = [
    # trajectory
    "Action",
    "ContextSnapshot",
    "RunStatus",
    "Step",
    "StepStatus",
    "StepType",
    "Trajectory",
    # evaluation
    "ComponentVerdict",
    "EndToEndVerdict",
    "EvaluationResult",
    "Evidence",
    "Verdict",
    # attribution
    "Attribution",
    "Counterfactual",
    "Repair",
    "RepairEdit",
]
