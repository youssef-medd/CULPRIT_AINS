"""The judge panel: one focused judge per step type plus the end-to-end judge.

A component judge is selected by ``StepType`` via ``component_judge_for``; the
end-to-end judge is separate because it produces a task-level verdict.
"""

from culprit.contracts.loader import Rubric
from culprit.evaluation.judges.backends import (
    HeuristicJudgeBackend,
    LLMJudgeBackend,
    default_backend,
)
from culprit.evaluation.judges.base import (
    BaseComponentJudge,
    ComponentJudgeRequest,
    EndToEndJudgeRequest,
    RawJudgment,
    load_prompt,
)
from culprit.evaluation.judges.end_to_end import EndToEndJudge
from culprit.evaluation.judges.planning import PlanningJudge
from culprit.evaluation.judges.retrieval import RetrievalJudge
from culprit.evaluation.judges.synthesis import SynthesisJudge
from culprit.evaluation.judges.tool_execution import ToolExecutionJudge
from culprit.schemas.trajectory import StepType

# Step type -> the component judge class that handles it.
COMPONENT_JUDGES: dict[StepType, type[BaseComponentJudge]] = {
    StepType.RETRIEVAL: RetrievalJudge,
    StepType.PLANNING: PlanningJudge,
    StepType.TOOL_EXECUTION: ToolExecutionJudge,
    StepType.SYNTHESIS: SynthesisJudge,
}


def component_judge_for(
    step_type: StepType, backend: object, rubric: Rubric | None = None
) -> BaseComponentJudge | None:
    """Instantiate the judge for ``step_type``, or ``None`` if untyped/unknown."""
    judge_cls = COMPONENT_JUDGES.get(step_type)
    return judge_cls(backend, rubric) if judge_cls else None


__all__ = [
    "BaseComponentJudge",
    "ComponentJudgeRequest",
    "EndToEndJudgeRequest",
    "RawJudgment",
    "load_prompt",
    "LLMJudgeBackend",
    "HeuristicJudgeBackend",
    "default_backend",
    "RetrievalJudge",
    "PlanningJudge",
    "ToolExecutionJudge",
    "SynthesisJudge",
    "EndToEndJudge",
    "COMPONENT_JUDGES",
    "component_judge_for",
]
