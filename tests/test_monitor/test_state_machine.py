"""Tests for the Shadow Monitor engine over trajectories."""

from culprit.monitor import build_monitor
from culprit.schemas.trajectory import Action, Step, StepType, Trajectory


def test_healthy_trajectory_no_alerts(good_trajectory):
    monitor = build_monitor()
    monitor.run(good_trajectory)
    assert monitor.diverged is False
    assert monitor.alerts == []


def _bad() -> Trajectory:
    return Trajectory(
        run_id="bad",
        steps=[
            Step(step_id="s0", step_index=0, span_name="plan", step_type=StepType.PLANNING),
            Step(step_id="s1", step_index=1, span_name="retrieve", step_type=StepType.RETRIEVAL,
                 action=Action(tool_name="search_tickets",
                               arguments={"product_area": "networking"})),
            Step(step_id="s2", step_index=2, span_name="act", step_type=StepType.TOOL_EXECUTION,
                 action=Action(tool_name="set_priority", arguments={"priority": "High"})),
            Step(step_id="s3", step_index=3, span_name="act", step_type=StepType.TOOL_EXECUTION,
                 action=Action(tool_name="set_team", arguments={"team": "Network Engineering"})),
        ],
    )


def test_out_of_order_trips_checkers():
    monitor = build_monitor()
    monitor.run(_bad())
    fired = {a.invariant_id for a in monitor.alerts}
    assert "retrieval_precedes_planning" in fired
    assert "set_team_before_set_priority" in fired


def test_first_alert_is_earliest():
    monitor = build_monitor()
    monitor.run(_bad())
    first = monitor.first_alert()
    assert first is not None
    assert first.step_index == min(a.step_index for a in monitor.alerts)
