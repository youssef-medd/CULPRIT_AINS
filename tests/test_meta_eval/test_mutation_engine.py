"""Tests for the trajectory mutation engine."""

from culprit.meta_eval.injector import FAULTS
from culprit.meta_eval.mutation_engine import MutationEngine


def test_fuzz_expands_each_base_by_all_faults(good_trajectory):
    cases = MutationEngine(seed=1).fuzz([good_trajectory, good_trajectory], shuffle=False)
    assert len(cases) == 2 * len(FAULTS)


def test_fuzz_tickets_skips_arealess(networking_ticket):
    tickets = [networking_ticket, {"id": "Q", "title": "vague", "product_area": None}]
    cases = MutationEngine(seed=0).fuzz_tickets(tickets)
    # only the well-specified ticket is fuzzed
    assert len(cases) == len(FAULTS)


def test_seed_is_reproducible(good_trajectory):
    a = [c.label.fault_type for c in MutationEngine(seed=7).fuzz([good_trajectory])]
    b = [c.label.fault_type for c in MutationEngine(seed=7).fuzz([good_trajectory])]
    assert a == b
