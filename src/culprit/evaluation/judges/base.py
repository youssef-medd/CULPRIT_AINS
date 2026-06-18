"""Judge abstractions: requests, raw judgments, and the component-judge base.

A judge's job is to assemble *focused context* for one step and delegate the
actual decision to a pluggable backend (LLM or deterministic heuristic). Keeping
"what context" (the judge) separate from "how to decide" (the backend) is what
lets the same judges run against a real model or, for tests and offline demos, a
deterministic stand-in.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, Field

from culprit.contracts.loader import Rubric, TaskSuccessContract
from culprit.schemas.evaluation import Evidence, Verdict
from culprit.schemas.trajectory import Step, StepType, Trajectory

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    """Load a prompt template by stem (e.g. ``"retrieval"``) from prompts/."""
    return (PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8")


class RawJudgment(BaseModel):
    """A backend's decision before self-consistency/confidence is applied."""

    verdict: Verdict = Verdict.UNKNOWN
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    failure_category: str | None = None
    rationale: str = ""
    evidence: list[Evidence] = Field(default_factory=list)


class ComponentJudgeRequest(BaseModel):
    """Everything a backend needs to judge one component step."""

    step: Step
    step_type: StepType
    rubric: Rubric | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    reference: dict[str, Any] | None = None
    prompt_template: str = ""


class EndToEndJudgeRequest(BaseModel):
    """Everything a backend needs for the task-level success verdict."""

    run_id: str
    ticket: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    task: TaskSuccessContract | None = None
    reference: dict[str, Any] | None = None
    prompt_template: str = ""


class BaseComponentJudge(ABC):
    """Base for per-step judges. Subclasses declare a type, prompt, and context."""

    step_type: ClassVar[StepType]
    prompt_name: ClassVar[str]

    def __init__(self, backend: Any, rubric: Rubric | None = None) -> None:
        self.backend = backend
        self.rubric = rubric

    @abstractmethod
    def extract_context(self, trajectory: Trajectory, step: Step) -> dict[str, Any]:
        """Return the focused context the judge is allowed to use for this step."""

    def reference(self, trajectory: Trajectory, step: Step) -> dict[str, Any] | None:
        """Optional gold reference for reference-based scoring (default: none)."""
        return None

    def build_request(self, trajectory: Trajectory, step: Step) -> ComponentJudgeRequest:
        """Assemble the backend request for this step."""
        return ComponentJudgeRequest(
            step=step,
            step_type=self.step_type,
            rubric=self.rubric,
            context=self.extract_context(trajectory, step),
            reference=self.reference(trajectory, step),
            prompt_template=load_prompt(self.prompt_name),
        )

    def judge_once(
        self, trajectory: Trajectory, step: Step, temperature: float = 0.0
    ) -> RawJudgment:
        """Produce a single (un-aggregated) judgment for this step."""
        return self.backend.judge_component(self.build_request(trajectory, step), temperature)
