"""Trajectory Mutation Engine: structure-aware fuzzing into a labeled corpus.

In the lineage of mutation/coverage fuzzing (DeepMutation, TensorFuzz) but
extended to agent *trajectories*: it takes known-good trajectories and applies
the structure-aware fault mutators (corrupting retrieval results, the plan, tool
arguments, or the summary) across every good base, yielding a large *labeled*
corpus. The label always comes from the injection, never from an LLM oracle.

Only faults that actually break the task outcome are emitted, since attribution
is gated on a failing run — that keeps every case in the corpus genuinely
attributable with known ground truth.
"""

from __future__ import annotations

import random
from collections.abc import Iterable
from typing import Any

from culprit.meta_eval.injector import InjectedCase, inject_all
from culprit.schemas.trajectory import Trajectory


class MutationEngine:
    """Expands good trajectories into many labeled failing ones."""

    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)

    def fuzz(
        self, good_trajectories: Iterable[Trajectory], shuffle: bool = True
    ) -> list[InjectedCase]:
        """Apply every fault mutator to every good base trajectory."""
        cases: list[InjectedCase] = []
        for trajectory in good_trajectories:
            cases.extend(inject_all(trajectory))
        if shuffle:
            self.rng.shuffle(cases)
        return cases

    def fuzz_tickets(
        self, tickets: Iterable[dict[str, Any]], shuffle: bool = True
    ) -> list[InjectedCase]:
        """Record good runs for well-specified tickets, then fuzz them.

        Tickets without a product area are skipped: their 'correct' routing is
        ambiguous, so they can't anchor a clean ground-truth label.
        """
        from culprit.recorder import record_run

        goods = [record_run(t) for t in tickets if t.get("product_area")]
        return self.fuzz(goods, shuffle=shuffle)
