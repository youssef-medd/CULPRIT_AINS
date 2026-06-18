"""Tests for the verdict renderer."""

from culprit.schemas.attribution import Attribution, Counterfactual, Repair, RepairEdit
from culprit.schemas.evaluation import Verdict
from culprit.schemas.trajectory import StepType
from culprit.verdict import VerdictRenderer


def _fail_attribution() -> Attribution:
    return Attribution(
        run_id="run_x",
        end_to_end_verdict=Verdict.FAIL,
        decisive_step_id="step_00",
        decisive_step_type=StepType.RETRIEVAL,
        failure_category="no_filter_applied",
        why="Retrieval ran unfiltered.",
        confidence=1.0,
        crs=1.0,
        confirmed=True,
        recommended_fix="Populate product_area.",
        counterfactual=Counterfactual(
            performed=True,
            confirms_attribution=True,
            minimal=True,
            repair=Repair(description="fix", edits=[RepairEdit(field="x", to_value="y")]),
        ),
    )


def test_pass_report():
    text = VerdictRenderer().render_text(
        Attribution(run_id="r", end_to_end_verdict=Verdict.PASS, why="all good")
    )
    assert "PASS" in text


def test_fail_report_contains_key_fields():
    text = VerdictRenderer().render_text(_fail_attribution())
    assert "FAIL" in text
    assert "step_00" in text
    assert "Populate product_area." in text


def test_write_creates_json_and_md(tmp_path):
    paths = VerdictRenderer().write(_fail_attribution(), output_dir=tmp_path)
    assert paths["json"].exists()
    assert paths["markdown"].exists()
    assert "run_x" in paths["json"].read_text(encoding="utf-8")
