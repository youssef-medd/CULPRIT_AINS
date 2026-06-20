"""Compile ordering invariants into runtime-verification checkers.

Each invariant becomes its own small stateful automaton (a ``Checker``). The
Shadow Monitor feeds every step to every checker as the run proceeds; a checker
returns a ``DivergenceAlert`` the first time its property is violated and then
stays quiet. Checking is over the *sequence of actions and capability*, never
exact text, so legitimately different valid paths never trip a checker.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from culprit.contracts.loader import Invariant, InvariantKind, OrderingContract
from culprit.monitor.alerts import DivergenceAlert
from culprit.schemas.trajectory import Step

# (tool_name, capability) -> bool. Resolves whether a tool provides a capability.
CapabilityResolver = Callable[[str, str], bool]


def default_capability_resolver(tool: str, capability: str) -> bool:
    """Resolve capability against the agent's tool registry (lazy import)."""
    from culprit.agent.tools import tool_can

    return tool_can(tool, capability)


def _provides_field(step: Step, field: str) -> bool:
    """True if this step actually makes ``field`` available with a real value.

    Checks the action arguments and (dict) result for a non-empty value. The
    context snapshot's ``available_fields`` is deliberately ignored — it lists
    field *names* that exist on the input, even when the value is null, which is
    exactly the degraded case we must catch.
    """
    empty: tuple[Any, ...] = (None, "", [], {})
    if step.action and step.action.arguments.get(field) not in empty:
        return True
    return isinstance(step.result, dict) and step.result.get(field) not in empty


class Checker(ABC):
    """A single-property runtime monitor. Fires at most once."""

    def __init__(self, invariant: Invariant) -> None:
        self.invariant = invariant
        self.fired = False

    @abstractmethod
    def observe(self, step: Step) -> DivergenceAlert | None:
        """Process one step; return an alert if it violates the property now."""

    def _alert(self, step: Step, message: str, **evidence: Any) -> DivergenceAlert:
        self.fired = True
        return DivergenceAlert(
            invariant_id=self.invariant.id,
            kind=self.invariant.kind.value,
            message=message,
            step_id=step.step_id,
            step_index=step.step_index,
            evidence=evidence,
        )


class PrecedesChecker(Checker):
    """``before`` step type must occur before any ``after`` step type."""

    def __init__(self, invariant: Invariant) -> None:
        super().__init__(invariant)
        self._before_seen = False

    def observe(self, step: Step) -> DivergenceAlert | None:
        if self.fired:
            return None
        if step.step_type == self.invariant.before:
            self._before_seen = True
        elif step.step_type == self.invariant.after and not self._before_seen:
            return self._alert(
                step,
                f"{self.invariant.after} occurred before any {self.invariant.before} step",
                before=str(self.invariant.before),
                after=str(self.invariant.after),
            )
        return None


class ToolOrderChecker(Checker):
    """``before_tool`` must be called before ``after_tool``."""

    def __init__(self, invariant: Invariant) -> None:
        super().__init__(invariant)
        self._before_seen = False

    def observe(self, step: Step) -> DivergenceAlert | None:
        if self.fired or step.action is None:
            return None
        tool = step.action.tool_name
        if tool == self.invariant.before_tool:
            self._before_seen = True
        elif tool == self.invariant.after_tool and not self._before_seen:
            return self._alert(
                step,
                f"{self.invariant.after_tool} was called before {self.invariant.before_tool}",
                before_tool=self.invariant.before_tool,
                after_tool=self.invariant.after_tool,
            )
        return None


class ToolCapabilityChecker(Checker):
    """When ``tool`` is used it must provide the declared ``capability``."""

    def __init__(self, invariant: Invariant, resolver: CapabilityResolver) -> None:
        super().__init__(invariant)
        self._resolver = resolver

    def observe(self, step: Step) -> DivergenceAlert | None:
        if self.fired or step.action is None:
            return None
        if step.action.tool_name == self.invariant.tool:
            capability = self.invariant.capability or ""
            if not self._resolver(self.invariant.tool, capability):
                return self._alert(
                    step,
                    f"tool {self.invariant.tool} is not capable of {capability}",
                    tool=self.invariant.tool,
                    capability=capability,
                )
        return None


class FieldAvailableChecker(Checker):
    """``field`` must be produced by a ``before`` step before an ``after`` step uses it."""

    def __init__(self, invariant: Invariant) -> None:
        super().__init__(invariant)
        self._available = False

    def observe(self, step: Step) -> DivergenceAlert | None:
        if self.fired:
            return None
        field = self.invariant.field or ""
        if step.step_type == self.invariant.before and _provides_field(step, field):
            self._available = True
        elif step.step_type == self.invariant.after and not self._available:
            return self._alert(
                step,
                f"{field} was used in {self.invariant.after} before being "
                f"retrieved in {self.invariant.before}",
                field=field,
            )
        return None


_BUILDERS: dict[InvariantKind, Callable[..., Checker]] = {
    InvariantKind.PRECEDES: PrecedesChecker,
    InvariantKind.TOOL_ORDER: ToolOrderChecker,
    InvariantKind.FIELD_AVAILABLE_BEFORE: FieldAvailableChecker,
}


def compile_checkers(
    ordering: OrderingContract,
    capability_resolver: CapabilityResolver | None = None,
) -> list[Checker]:
    """Compile every invariant in ``ordering`` into a runtime checker."""
    resolver = capability_resolver or default_capability_resolver
    checkers: list[Checker] = []
    for inv in ordering.invariants:
        if inv.kind == InvariantKind.TOOL_CAPABILITY:
            checkers.append(ToolCapabilityChecker(inv, resolver))
        else:
            checkers.append(_BUILDERS[inv.kind](inv))
    return checkers
