"""Append-only SQLite store for trajectories.

The full typed ``Trajectory`` is persisted as JSON in one row, with a few
columns lifted out for cheap querying (run_id, ticket_id, final_status,
created_at). SQLite now; the schema is intentionally simple so it can move to
Postgres at scale, with trajectories staying append-only.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from culprit.config import settings
from culprit.schemas.trajectory import Trajectory

_SCHEMA = """
CREATE TABLE IF NOT EXISTS trajectories (
    run_id       TEXT PRIMARY KEY,
    ticket_id    TEXT,
    final_status TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    payload      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_trajectories_ticket ON trajectories (ticket_id);
CREATE INDEX IF NOT EXISTS ix_trajectories_status ON trajectories (final_status);
"""


class TrajectoryStore:
    """Thin persistence layer over a SQLite database of trajectories."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path else settings.db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def save(self, trajectory: Trajectory) -> None:
        """Persist a trajectory (idempotent on run_id)."""
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO trajectories "
                "(run_id, ticket_id, final_status, created_at, payload) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    trajectory.run_id,
                    trajectory.ticket_id,
                    trajectory.final_status.value,
                    datetime.now(timezone.utc).isoformat(),
                    trajectory.model_dump_json(),
                ),
            )

    def get(self, run_id: str) -> Trajectory | None:
        """Load a trajectory by run_id, or ``None`` if absent."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM trajectories WHERE run_id = ?", (run_id,)
            ).fetchone()
        return Trajectory.model_validate_json(row["payload"]) if row else None

    def all_run_ids(self) -> list[str]:
        """Return every stored run_id, oldest first."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT run_id FROM trajectories ORDER BY created_at"
            ).fetchall()
        return [r["run_id"] for r in rows]

    def count(self) -> int:
        """Return the number of stored trajectories."""
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM trajectories").fetchone()[0]
