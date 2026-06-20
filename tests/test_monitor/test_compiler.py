"""Tests for compiling invariants into checkers."""

from culprit.contracts import load_contracts
from culprit.monitor.compiler import (
    Checker,
    FieldAvailableChecker,
    PrecedesChecker,
    _provides_field,
    compile_checkers,
)
from culprit.schemas.trajectory import Action, ContextSnapshot, Step


def test_compiles_one_checker_per_invariant():
    ordering = load_contracts().ordering
    checkers = compile_checkers(ordering)
    assert len(checkers) == len(ordering.invariants)
    assert all(isinstance(c, Checker) for c in checkers)


def test_checker_kinds_present():
    checkers = compile_checkers(load_contracts().ordering)
    kinds = {type(c) for c in checkers}
    assert PrecedesChecker in kinds
    assert FieldAvailableChecker in kinds


def test_provides_field_requires_real_value():
    has = Step(step_id="s", step_index=0, span_name="retrieve",
               action=Action(tool_name="search_tickets", arguments={"product_area": "networking"}))
    missing = Step(step_id="s", step_index=0, span_name="retrieve",
                   action=Action(tool_name="search_tickets", arguments={"product_area": None}),
                   context_snapshot=ContextSnapshot(available_fields=["product_area"]))
    assert _provides_field(has, "product_area") is True
    # available_fields lists the name even when null -> must NOT count as provided
    assert _provides_field(missing, "product_area") is False
