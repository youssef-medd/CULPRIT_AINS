"""Cheap-LLM fallback for step typing.

Only invoked for steps the rules left ``UNKNOWN``. Uses the cheap tagger model
and lazily imports ``openai`` so this module imports without it. On any
problem (no SDK, no key, unparseable reply) it returns ``UNKNOWN`` rather than
guessing — a mislabel is worse than an honest unknown.
"""

from __future__ import annotations

from culprit.schemas.trajectory import Step, StepType

_VALID = {t.value for t in StepType}


def llm_tag_step(step: Step, model: str | None = None) -> StepType:
    """Classify a single step into a ``StepType`` via the cheap model."""
    try:
        from openai import OpenAI
    except ImportError:
        return StepType.UNKNOWN

    from culprit.config import settings

    if not settings.nvidia_api_key:
        return StepType.UNKNOWN

    tool = step.action.tool_name if step.action else None
    prompt = (
        "Classify this AI-agent step into exactly one type from "
        f"{sorted(_VALID)}.\n"
        f"span_name: {step.span_name}\n"
        f"tool: {tool}\n"
        f"reasoning: {(step.reasoning or '')[:300]}\n"
        "Answer with the single type word only."
    )
    try:
        client = OpenAI(base_url=settings.nvidia_base_url, api_key=settings.nvidia_api_key)
        completion = client.chat.completions.create(
            model=model or settings.tagger_model,
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )
        answer = (completion.choices[0].message.content or "").strip().lower()
        return StepType(answer) if answer in _VALID else StepType.UNKNOWN
    except Exception:
        return StepType.UNKNOWN
