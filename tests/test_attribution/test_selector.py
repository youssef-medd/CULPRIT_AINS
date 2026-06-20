"""Tests for decisive-step selection."""

from culprit.attribution.selector import earliest_failing, select_suspects
from culprit.schemas.evaluation import (
    ComponentVerdict,
    EndToEndVerdict,
    EvaluationResult,
    Verdict,
)
from culprit.schemas.trajectory import Step, StepType, Trajectory


def _traj():
    return Trajectory(
        run_id="r",
        steps=[
            Step(
                step_id="step_00", step_index=0, span_name="retrieve",
                step_type=StepType.RETRIEVAL,
            ),
            Step(step_id="step_01", step_index=1, span_name="plan", step_type=StepType.PLANNING),
            Step(
                step_id="step_04", step_index=4, span_name="synthesize",
                step_type=StepType.SYNTHESIS,
            ),
        ],
    )


def _eval():
    return EvaluationResult(
        run_id="r",
        end_to_end=EndToEndVerdict(verdict=Verdict.FAIL, confidence=0.9),
        component_verdicts=[
            ComponentVerdict(
                step_id="step_04", step_type=StepType.SYNTHESIS,
                verdict=Verdict.FAIL, confidence=0.9,
            ),
            ComponentVerdict(
                step_id="step_00", step_type=StepType.RETRIEVAL,
                verdict=Verdict.FAIL, confidence=0.9,
            ),
        ],
    )


def test_suspects_ordered_earliest_first():
    suspects = select_suspects(_traj(), _eval(), alerts=[], tau=0.7)
    assert [s.step_id for s in suspects] == ["step_00", "step_04"]


def test_tau_filters_low_confidence():
    ev = _eval()
    ev.component_verdicts[1].confidence = 0.4  # retrieval below tau
    suspects = select_suspects(_traj(), ev, alerts=[], tau=0.7)
    assert [s.step_id for s in suspects] == ["step_04"]


def test_earliest_failing_ignores_tau():
    ev = _eval()
    for v in ev.component_verdicts:
        v.confidence = 0.1
    assert earliest_failing(_traj(), ev).step_id == "step_00"
