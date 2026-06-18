"""Tests for the JSM triage agent graph."""

from culprit.agent import run_triage


def test_routes_networking_to_network_engineering(networking_ticket):
    state = run_triage(networking_ticket)
    assert state["plan"]["team"] == "Network Engineering"
    assert state["status"] == "task_succeeded"
    # search + set_team + set_priority recorded
    assert len(state["tool_calls"]) == 3


def test_missing_area_runs_unfiltered_retrieval():
    state = run_triage({"id": "X", "title": "something broke", "product_area": None})
    search = state["tool_calls"][0]["result"]
    assert search["filtered"] is False


def test_set_team_precedes_set_priority(networking_ticket):
    state = run_triage(networking_ticket)
    tools = [c["tool"] for c in state["tool_calls"]]
    assert tools.index("set_team") < tools.index("set_priority")
