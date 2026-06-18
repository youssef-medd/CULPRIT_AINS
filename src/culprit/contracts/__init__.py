"""Behavioral contracts: the spec Culprit judges runs against.

Re-exports the contract models and loaders so callers can simply::

    from culprit.contracts import load_contracts
    contracts = load_contracts()
    rubric = contracts.rubric_for(StepType.RETRIEVAL)
"""

from culprit.contracts.loader import (
    ContractError,
    ContractStore,
    Criterion,
    FailureCategory,
    Invariant,
    InvariantKind,
    OrderingContract,
    Rubric,
    TaskSuccessContract,
    load_contracts,
    load_ordering,
    load_rubric,
    load_task_success,
)

__all__ = [
    "ContractError",
    "ContractStore",
    "Criterion",
    "FailureCategory",
    "Invariant",
    "InvariantKind",
    "OrderingContract",
    "Rubric",
    "TaskSuccessContract",
    "load_contracts",
    "load_ordering",
    "load_rubric",
    "load_task_success",
]
