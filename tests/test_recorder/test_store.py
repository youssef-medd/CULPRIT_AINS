"""Unit tests for the TrajectoryStore persistence layer."""

import pytest
from culprit.recorder.store import TrajectoryStore
from culprit.schemas.trajectory import RunStatus, Step, Trajectory


def _make_traj(run_id: str) -> Trajectory:
    return Trajectory(
        run_id=run_id,
        ticket_id=f"TICKET-{run_id}",
        steps=[
            Step(step_id=f"{run_id}_s0", step_index=0, span_name="retrieve"),
        ],
        final_status=RunStatus.SUCCEEDED,
    )


def test_count_empty(tmp_path):
    store = TrajectoryStore(db_path=tmp_path / "empty.db")
    assert store.count() == 0


def test_all_run_ids_empty(tmp_path):
    store = TrajectoryStore(db_path=tmp_path / "empty2.db")
    assert store.all_run_ids() == []


def test_get_nonexistent(tmp_path):
    store = TrajectoryStore(db_path=tmp_path / "nonexist.db")
    assert store.get("no_such_run") is None


def test_save_and_get(tmp_path):
    store = TrajectoryStore(db_path=tmp_path / "sg.db")
    traj = _make_traj("run_001")
    store.save(traj)
    loaded = store.get("run_001")
    assert loaded is not None
    assert loaded.run_id == "run_001"
    assert loaded.ticket_id == "TICKET-run_001"
    assert loaded.model_dump() == traj.model_dump()


def test_count_after_save(tmp_path):
    store = TrajectoryStore(db_path=tmp_path / "count.db")
    assert store.count() == 0
    store.save(_make_traj("r1"))
    assert store.count() == 1
    store.save(_make_traj("r2"))
    assert store.count() == 2


def test_all_run_ids_ordered(tmp_path):
    store = TrajectoryStore(db_path=tmp_path / "order.db")
    store.save(_make_traj("r2"))
    store.save(_make_traj("r1"))
    store.save(_make_traj("r3"))
    ids = store.all_run_ids()
    assert ids == ["r2", "r1", "r3"]


def test_save_duplicate_run_id_raises(tmp_path):
    store = TrajectoryStore(db_path=tmp_path / "dup.db")
    traj = _make_traj("dup_run")
    store.save(traj)
    with pytest.raises(Exception):
        store.save(traj)


def test_trajectory_serializes_all_fields(tmp_path):
    store = TrajectoryStore(db_path=tmp_path / "full.db")
    traj = _make_traj("full_run")
    store.save(traj)
    loaded = store.get("full_run")
    assert loaded is not None
    assert loaded.metadata is not None
    assert loaded.final_status == RunStatus.SUCCEEDED
