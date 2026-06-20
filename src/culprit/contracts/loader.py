"""Load and validate the behavioral spec from YAML into typed models.

The contracts are the statute Culprit judges against. They split into three
kinds, each feeding a different consumer:

* **Rubrics** (one per step type) — the semantic spec the LLM judges score against.
* **Ordering invariants** — structural rules the Shadow Monitor compiles into a
  runtime state machine.
* **Task-success** — the end-to-end definition of "correct" for the e2e judge.

Everything is validated on load so a malformed contract fails loudly here rather
than producing a silently-wrong verdict downstream.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel, Field, ValidationError

from culprit.config import settings
from culprit.schemas.trajectory import StepType


class ContractError(Exception):
    """Raised when a contract file is missing, unparseable, or invalid."""


# --------------------------------------------------------------------------- #
# Rubric models (semantic layer — consumed by the LLM judges)
# --------------------------------------------------------------------------- #
class Criterion(BaseModel):
    """One scored expectation within a rubric."""

    id: str
    description: str
    weight: float = Field(default=1.0, ge=0.0)


class FailureCategory(BaseModel):
    """A named way this component can fail — the label attribution assigns."""

    id: str
    description: str


class Rubric(BaseModel):
    """The behavioral spec for a single step type."""

    step_type: StepType
    version: int = Field(default=1, ge=1)
    description: str = ""
    reference_based: bool = False
    criteria: list[Criterion] = Field(default_factory=list)
    failure_categories: list[FailureCategory] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Ordering invariants (structural layer — compiled by the Shadow Monitor)
# --------------------------------------------------------------------------- #
class InvariantKind(StrEnum):
    """The structural rule families the Shadow Monitor can enforce.

    Deliberately minimal and about *ordering/capability over actions* — never
    exact text — so legitimately different valid paths don't trip the monitor.
    """

    PRECEDES = "precedes"  # step type `before` must occur before `after`
    TOOL_ORDER = "tool_order"  # tool `before_tool` must be called before `after_tool`
    TOOL_CAPABILITY = "tool_capability"  # `tool` must be capable of the requested action
    FIELD_AVAILABLE_BEFORE = "field_available_before"  # `field` retrieved before it is used


class Invariant(BaseModel):
    """One structural rule. Unused fields stay ``None`` per ``kind``."""

    id: str
    description: str
    kind: InvariantKind
    # PRECEDES: step-type ordering.
    before: StepType | None = None
    after: StepType | None = None
    # TOOL_ORDER: tool-name ordering within the action phase.
    before_tool: str | None = None
    after_tool: str | None = None
    # TOOL_CAPABILITY / FIELD_AVAILABLE_BEFORE.
    tool: str | None = None
    capability: str | None = None
    field: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class OrderingContract(BaseModel):
    """The set of structural invariants for the agent."""

    version: int = Field(default=1, ge=1)
    invariants: list[Invariant] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Task-success (end-to-end layer — consumed by the e2e judge)
# --------------------------------------------------------------------------- #
class TaskSuccessContract(BaseModel):
    """What it means for the whole run to succeed."""

    version: int = Field(default=1, ge=1)
    description: str = ""
    required_outputs: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Bundle + loaders
# --------------------------------------------------------------------------- #
class ContractStore(BaseModel):
    """All contracts loaded and indexed for the pipeline."""

    rubrics: dict[StepType, Rubric] = Field(default_factory=dict)
    ordering: OrderingContract = Field(default_factory=OrderingContract)
    task_success: TaskSuccessContract = Field(default_factory=TaskSuccessContract)

    def rubric_for(self, step_type: StepType) -> Rubric | None:
        """Return the rubric governing ``step_type``, or ``None``."""
        return self.rubrics.get(step_type)


def _read_yaml(path: Path) -> dict[str, Any]:
    """Parse a YAML file into a dict, raising ``ContractError`` on any problem."""
    if not path.exists():
        raise ContractError(f"Contract file not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:  # pragma: no cover - exercised via load tests
        raise ContractError(f"Failed to parse YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ContractError(f"Expected a mapping at the top of {path}, got {type(data).__name__}")
    return data


_ModelT = TypeVar("_ModelT", bound=BaseModel)


def _validate(model: type[_ModelT], data: dict[str, Any], path: Path) -> _ModelT:
    """Validate ``data`` against ``model``, re-raising as ``ContractError``."""
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise ContractError(f"Invalid contract {path}:\n{exc}") from exc


def load_rubric(path: Path) -> Rubric:
    """Load and validate a single rubric YAML file."""
    return _validate(Rubric, _read_yaml(path), path)


def load_ordering(path: Path) -> OrderingContract:
    """Load and validate the ordering-invariants YAML file."""
    return _validate(OrderingContract, _read_yaml(path), path)


def load_task_success(path: Path) -> TaskSuccessContract:
    """Load and validate the task-success YAML file."""
    return _validate(TaskSuccessContract, _read_yaml(path), path)


def load_contracts(contracts_dir: Path | None = None) -> ContractStore:
    """Load the entire contract set from ``contracts_dir`` (defaults to config).

    Layout expected under the directory::

        rubrics/*.yaml          one rubric per step type
        invariants/ordering.yaml
        task_success.yaml
    """
    root = contracts_dir or settings.contracts_dir

    rubrics: dict[StepType, Rubric] = {}
    rubric_dir = root / "rubrics"
    for rubric_path in sorted(rubric_dir.glob("*.yaml")):
        rubric = load_rubric(rubric_path)
        if rubric.step_type in rubrics:
            raise ContractError(f"Duplicate rubric for step type {rubric.step_type}")
        rubrics[rubric.step_type] = rubric

    ordering = load_ordering(root / "invariants" / "ordering.yaml")
    task_success = load_task_success(root / "task_success.yaml")

    return ContractStore(rubrics=rubrics, ordering=ordering, task_success=task_success)
