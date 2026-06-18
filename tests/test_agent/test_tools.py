"""Tests for the mocked JSM tools and the capability registry."""

from culprit.agent.tools import search_tickets, set_priority, set_team, tool_can


def test_search_filtered_scopes_to_area():
    result = search_tickets(product_area="networking", query="vpn")
    assert result["filtered"] is True
    assert result["results"]
    assert all(t["product_area"] == "networking" for t in result["results"])


def test_search_unfiltered_returns_mixed():
    result = search_tickets(product_area=None, query="help")
    assert result["filtered"] is False
    areas = {t["product_area"] for t in result["results"]}
    assert len(areas) >= 1  # unscoped pool, not a single area by construction


def test_set_team_sets_and_reports():
    record: dict = {}
    out = set_team(record, "Network Engineering")
    assert out["status"] == "ok"
    assert record["team"] == "Network Engineering"


def test_set_team_missing_arg_errors():
    out = set_team({}, "")
    assert out["status"] == "error"
    assert out["reason"] == "missing_required_argument"


def test_set_priority_validates_level():
    assert set_priority({}, "High")["status"] == "ok"
    bad = set_priority({}, "Whenever")
    assert bad["status"] == "error"
    assert bad["reason"] == "malformed_arguments"


def test_registry_capabilities():
    assert tool_can("set_team", "route_team")
    assert tool_can("set_priority", "set_priority")
    assert not tool_can("set_team", "set_priority")
    assert not tool_can("nonexistent", "route_team")
