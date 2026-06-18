"""Tests for fault injection."""

import pytest

from culprit.meta_eval.injector import FAULTS, inject, inject_all
from culprit.schemas.trajectory import StepType


def test_inject_all_covers_every_fault(good_trajectory):
    cases = inject_all(good_trajectory)
    assert len(cases) == len(FAULTS)
    assert {c.label.fault_type for c in cases} == set(FAULTS)


@pytest.mark.parametrize(
    "fault_type,component",
    [
        ("retrieval_no_filter", StepType.RETRIEVAL),
        ("planning_wrong_team", StepType.PLANNING),
        ("tool_missing_arg", StepType.TOOL_EXECUTION),
        ("synthesis_inconsistent", StepType.SYNTHESIS),
    ],
)
def test_label_component_matches(good_trajectory, fault_type, component):
    case = inject(good_trajectory, fault_type)
    assert case.label.component == component
    # the labeled step exists in the corrupted trajectory
    assert case.trajectory.step_by_id(case.label.step_id) is not None


def test_injection_does_not_mutate_original(good_trajectory):
    before = good_trajectory.model_dump_json()
    inject(good_trajectory, "retrieval_no_filter")
    assert good_trajectory.model_dump_json() == before
