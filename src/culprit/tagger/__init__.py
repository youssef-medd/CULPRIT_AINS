"""Step Tagger: label each trajectory step with a ``StepType``.

Rule-based on tool/span name (the cheap, primary path) with an optional
cheap-LLM fallback for ambiguous steps::

    from culprit.tagger import tag_trajectory
    tag_trajectory(trajectory)  # fills step_type for every UNKNOWN step
"""

from culprit.tagger.llm_fallback import llm_tag_step
from culprit.tagger.rules import (
    SPAN_TO_TYPE,
    TOOL_TO_TYPE,
    tag_step_type,
    tag_trajectory,
)

__all__ = [
    "tag_step_type",
    "tag_trajectory",
    "llm_tag_step",
    "TOOL_TO_TYPE",
    "SPAN_TO_TYPE",
]
