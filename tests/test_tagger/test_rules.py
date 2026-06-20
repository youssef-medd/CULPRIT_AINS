"""Tests for the rule-based step tagger."""

from culprit.schemas.trajectory import Action, Step, StepType, Trajectory
from culprit.tagger import tag_step_type, tag_trajectory


def test_tool_name_wins():
    assert tag_step_type("anything", "search_tickets") == StepType.RETRIEVAL
    assert tag_step_type("anything", "set_team") == StepType.TOOL_EXECUTION


def test_span_name_mapping():
    assert tag_step_type("plan") == StepType.PLANNING
    assert tag_step_type("synthesize") == StepType.SYNTHESIS


def test_keyword_fallback():
    assert tag_step_type("retrieve_similar") == StepType.RETRIEVAL
    assert tag_step_type("summarize_result") == StepType.SYNTHESIS


def test_unknown_when_no_signal():
    assert tag_step_type("frobnicate") == StepType.UNKNOWN


def test_tag_trajectory_fills_unknown():
    traj = Trajectory(
        run_id="r",
        steps=[
            Step(step_id="s0", step_index=0, span_name="retrieve",
                 action=Action(tool_name="search_tickets")),
            Step(step_id="s1", step_index=1, span_name="plan"),
        ],
    )
    tag_trajectory(traj)
    assert traj.steps[0].step_type == StepType.RETRIEVAL
    assert traj.steps[1].step_type == StepType.PLANNING
