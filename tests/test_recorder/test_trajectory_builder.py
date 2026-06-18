"""Tests for trajectory capture, tagging, and the store round-trip."""

from culprit.recorder import TrajectoryStore, record_run
from culprit.schemas.trajectory import StepType


def test_trajectory_has_typed_ordered_steps(good_trajectory):
    types = [s.step_type for s in good_trajectory.ordered()]
    assert types == [
        StepType.RETRIEVAL,
        StepType.PLANNING,
        StepType.TOOL_EXECUTION,
        StepType.TOOL_EXECUTION,
        StepType.SYNTHESIS,
    ]
    assert all(s.step_type != StepType.UNKNOWN for s in good_trajectory.steps)


def test_step_ids_are_sequential(good_trajectory):
    ids = [s.step_id for s in good_trajectory.ordered()]
    assert ids == [f"step_{i:02d}" for i in range(len(ids))]


def test_store_round_trip(tmp_path, networking_ticket):
    store = TrajectoryStore(db_path=tmp_path / "t.db")
    traj = record_run(networking_ticket, store=store)
    assert store.count() == 1
    loaded = store.get(traj.run_id)
    assert loaded is not None
    assert loaded.model_dump() == traj.model_dump()
