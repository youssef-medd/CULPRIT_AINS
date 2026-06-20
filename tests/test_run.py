"""Tests for the top-level pipeline entry point in ``culprit.run``."""

from __future__ import annotations

from types import SimpleNamespace

from culprit import run as run_module


def test_load_tickets_ignores_blank_lines(tmp_path):
    path = tmp_path / "tickets.jsonl"
    path.write_text(
        "\n"
        '{"id": "one", "title": "First"}\n'
        "   \n"
        '{"id": "two", "title": "Second"}\n',
        encoding="utf-8",
    )

    tickets = run_module.load_tickets(path)

    assert tickets == [
        {"id": "one", "title": "First"},
        {"id": "two", "title": "Second"},
    ]


def test_main_returns_error_for_missing_tickets_file(tmp_path, capsys):
    missing = tmp_path / "missing.jsonl"

    exit_code = run_module.main(["--tickets", str(missing)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert f"error: tickets file not found: {missing}" in captured.err


def test_main_prints_summary_for_successful_run(monkeypatch, tmp_path, capsys):
    tickets_path = tmp_path / "tickets.jsonl"
    tickets_path.write_text('{"id": "one"}\n', encoding="utf-8")

    attribution = SimpleNamespace(
        is_pass=False,
        confirmed=True,
        decisive_step_id="step_00",
        decisive_step_type="retrieval",
        recommended_fix="Populate product_area.",
    )
    reports = [SimpleNamespace(run_id="run_123", verdict="fail", attribution=attribution)]

    monkeypatch.setattr(run_module, "load_tickets", lambda path: [{"id": "one"}])
    monkeypatch.setattr(run_module, "run_pipeline", lambda tickets, output_dir: reports)

    exit_code = run_module.main(
        ["--tickets", str(tickets_path), "--output-dir", str(tmp_path / "out")]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Evaluated 1 run(s). Verdicts written to" in captured.out
    assert "run_123" in captured.out
    assert "step_00 retrieval [confirmed] :: Populate product_area." in captured.out