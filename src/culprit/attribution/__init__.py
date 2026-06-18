"""Attribution (E3): name the decisive component, prove it, recommend a fix.

Combines the earliest-high-confidence-suspect rule with counterfactual
confirmation::

    from culprit.attribution import attribute
    report = attribute(trajectory, evaluation, alerts=monitor.alerts)
    report.decisive_step_id, report.confirmed, report.crs, report.recommended_fix
"""

from culprit.attribution.counterfactual import CounterfactualEngine
from culprit.attribution.crs import causal_responsibility
from culprit.attribution.engine import AttributionEngine, attribute
from culprit.attribution.selector import Suspect, earliest_failing, select_suspects

__all__ = [
    "attribute",
    "AttributionEngine",
    "select_suspects",
    "earliest_failing",
    "Suspect",
    "CounterfactualEngine",
    "causal_responsibility",
]
