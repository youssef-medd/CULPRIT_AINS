"""Shared test fixtures and path setup.

Puts ``src`` on the import path so tests run without an editable install, and
provides a clean recorded trajectory plus a heuristic-backed judge runner.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest  # noqa: E402

NETWORKING_TICKET = {
    "id": "JSM-TEST",
    "title": "VPN keeps dropping, cannot work",
    "description": "Since this morning the VPN disconnects and is blocking my work.",
    "product_area": "networking",
}


@pytest.fixture
def networking_ticket() -> dict:
    return dict(NETWORKING_TICKET)


@pytest.fixture
def good_trajectory():
    """A clean, recorded trajectory for a well-specified ticket."""
    from culprit.recorder import record_run

    return record_run(NETWORKING_TICKET)


@pytest.fixture
def runner():
    """A JudgeRunner on the deterministic heuristic backend."""
    from culprit.evaluation import JudgeRunner
    from culprit.evaluation.judges import HeuristicJudgeBackend

    return JudgeRunner(backend=HeuristicJudgeBackend())
