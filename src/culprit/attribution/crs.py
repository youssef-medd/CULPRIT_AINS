"""Causal Responsibility Score (CRS).

A defined [0,1] measure of how responsible the decisive step is for the failure.
It rewards three things, in priority order:

* **Causal confirmation** (weight 0.5) — did counterfactual replay actually flip
  the outcome to success? An intervention that flips the result is the strongest
  evidence of responsibility (Pearl's interventional rung beats correlation).
* **Judge confidence** (weight 0.4) — how sure the evaluation layer was.
* **Minimality** (weight 0.1) — a single-variable fix that flips the outcome
  pins responsibility more precisely than a coarse correction.

This is a heuristic we define, not a standard metric; it is reported alongside
the evidence so a reader can weigh it themselves.
"""

from __future__ import annotations

_W_CONFIRMED = 0.5
_W_CONFIDENCE = 0.4
_W_MINIMAL = 0.1


def causal_responsibility(confidence: float, confirmed: bool, minimal: bool) -> float:
    """Compute the CRS from confidence and counterfactual outcome flags."""
    score = (
        _W_CONFIDENCE * confidence
        + _W_CONFIRMED * (1.0 if confirmed else 0.0)
        + _W_MINIMAL * (1.0 if minimal else 0.0)
    )
    return round(min(1.0, max(0.0, score)), 3)
