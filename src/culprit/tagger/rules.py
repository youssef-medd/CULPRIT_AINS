"""Rule-based step typing.

Labels each step with a ``StepType`` from its span name and (when present) the
tool it called. Deterministic and cheap — this is the primary path; only steps
that stay ``UNKNOWN`` fall through to the optional LLM tagger. Typing is what
lets the judges and the attribution engine localize a failure to one component.
"""

from __future__ import annotations

from culprit.schemas.trajectory import StepType, Trajectory

# Tool name -> step type (most reliable signal).
TOOL_TO_TYPE: dict[str, StepType] = {
    "search_tickets": StepType.RETRIEVAL,
    "set_team": StepType.TOOL_EXECUTION,
    "set_priority": StepType.TOOL_EXECUTION,
    "add_comment": StepType.TOOL_EXECUTION,
}

# Graph node / span name -> step type.
SPAN_TO_TYPE: dict[str, StepType] = {
    "retrieve": StepType.RETRIEVAL,
    "plan": StepType.PLANNING,
    "act": StepType.TOOL_EXECUTION,
    "synthesize": StepType.SYNTHESIS,
}

# Substring heuristics for spans we don't recognize exactly.
_KEYWORD_RULES: list[tuple[tuple[str, ...], StepType]] = [
    (("retriev", "search", "lookup"), StepType.RETRIEVAL),
    (("plan", "classif", "decide", "route"), StepType.PLANNING),
    (("tool", "act", "execut", "call"), StepType.TOOL_EXECUTION),
    (("synth", "summar", "respond", "compose"), StepType.SYNTHESIS),
]


def tag_step_type(span_name: str | None, tool_name: str | None = None) -> StepType:
    """Return the step type for a span, preferring the tool-name signal."""
    if tool_name and tool_name in TOOL_TO_TYPE:
        return TOOL_TO_TYPE[tool_name]

    span = (span_name or "").lower()
    if span in SPAN_TO_TYPE:
        return SPAN_TO_TYPE[span]

    for keywords, step_type in _KEYWORD_RULES:
        if any(kw in span for kw in keywords):
            return step_type

    return StepType.UNKNOWN


def tag_trajectory(trajectory: Trajectory, use_llm_fallback: bool = False) -> Trajectory:
    """Assign a ``StepType`` to every still-``UNKNOWN`` step, in place.

    Tries the rules first; only when a step is still ``UNKNOWN`` and
    ``use_llm_fallback`` is set does it consult the cheap-LLM tagger.
    """
    for step in trajectory.steps:
        if step.step_type != StepType.UNKNOWN:
            continue
        tool_name = step.action.tool_name if step.action else None
        step_type = tag_step_type(step.span_name, tool_name)

        if step_type == StepType.UNKNOWN and use_llm_fallback:
            from culprit.tagger.llm_fallback import llm_tag_step

            step_type = llm_tag_step(step)

        step.step_type = step_type
    return trajectory
