"""Tests for the Causal Responsibility Score (CRS) computation."""

import pytest
from culprit.attribution.crs import causal_responsibility


def test_crs_zero_when_no_evidence():
    assert causal_responsibility(confidence=0.0, confirmed=False, minimal=False) == 0.0


def test_crs_full_when_all_positive():
    assert causal_responsibility(confidence=1.0, confirmed=True, minimal=True) == 1.0


def test_crs_dominates_confidence():
    crs_high = causal_responsibility(confidence=1.0, confirmed=True, minimal=True)
    crs_low = causal_responsibility(confidence=0.3, confirmed=True, minimal=True)
    assert crs_high > crs_low


def test_crs_confirmed_weighs_more_than_confidence():
    unconfirmed_high = causal_responsibility(confidence=1.0, confirmed=False, minimal=False)
    confirmed_low = causal_responsibility(confidence=0.0, confirmed=True, minimal=False)
    assert confirmed_low > unconfirmed_high


def test_crs_minimality_contributes():
    with_minimal = causal_responsibility(confidence=0.5, confirmed=True, minimal=True)
    without_minimal = causal_responsibility(confidence=0.5, confirmed=True, minimal=False)
    assert with_minimal > without_minimal


def test_crs_bound_clamped():
    assert causal_responsibility(confidence=1.5, confirmed=True, minimal=True) == 1.0
    assert causal_responsibility(confidence=-0.5, confirmed=False, minimal=False) == 0.0


def test_crs_rounding():
    result = causal_responsibility(confidence=0.3333, confirmed=False, minimal=False)
    assert result == round(0.4 * 0.3333, 3)
