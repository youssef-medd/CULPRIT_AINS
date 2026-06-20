"""Plan node: classify the ticket and decide the triage actions.

The planner is pluggable behind the ``Planner`` protocol:

* ``RuleBasedPlanner`` — deterministic, no API key. Routes by majority team of
  the retrieved tickets (falling back to a product-area map) and infers priority
  from severity keywords. This is the "determinism as a feature" path used for
  fixtures, replay, and tests. Because it routes off the *retrieved* tickets, a
  bad retrieval cascades into a wrong team here — the exact failure the README
  describes.
* ``LLMPlanner`` — calls NVIDIA (OpenAI-compatible API) for genuinely
  non-deterministic behavior. Imported lazily so this module never hard-depends
  on ``openai``.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Protocol

from culprit.agent.state import AgentState, Plan

# Product area -> owning team, used when retrieval gives no usable signal.
PRODUCT_AREA_TEAM: dict[str, str] = {
    "networking": "Network Engineering",
    "printing": "IT Hardware Support",
    "email": "Messaging & Collaboration",
    "identity": "Identity & Access Management",
    "software": "Application Support",
}

# Severity keyword -> priority, scanned highest-first.
_PRIORITY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("Critical", ("outage", "down for everyone", "company-wide", "data loss")),
    ("High", ("cannot work", "blocked", "urgent", "locked out", "entire", "all users")),
    ("Medium", ("slow", "intermittent", "sometimes", "degraded")),
    ("Low", ("question", "how do i", "request", "cosmetic", "typo")),
]


def infer_priority(ticket: dict[str, Any]) -> str:
    """Infer a priority from the ticket's text via severity keywords."""
    text = f"{ticket.get('title', '')} {ticket.get('description', '')}".lower()
    for priority, keywords in _PRIORITY_RULES:
        if any(kw in text for kw in keywords):
            return priority
    return "Medium"


class Planner(Protocol):
    """Anything that can turn a ticket + retrieved context into a Plan."""

    def classify(self, ticket: dict[str, Any], retrieved: list[dict[str, Any]]) -> Plan: ...


class RuleBasedPlanner:
    """Deterministic planner: majority-vote team + keyword priority."""

    def classify(self, ticket: dict[str, Any], retrieved: list[dict[str, Any]]) -> Plan:
        teams = [r["team"] for r in retrieved if r.get("team")]
        if teams:
            team = Counter(teams).most_common(1)[0][0]
            basis = "majority of retrieved tickets"
        else:
            team = PRODUCT_AREA_TEAM.get((ticket.get("product_area") or "").lower())
            basis = "product-area fallback"

        priority = infer_priority(ticket)
        rationale = (
            f"Routed to {team} ({basis}); priority {priority} inferred from the ticket text."
        )
        return Plan(
            team=team,
            priority=priority,
            planned_actions=["set_team", "set_priority"],
            rationale=rationale,
        )


class LLMPlanner:
    """Non-deterministic planner backed by NVIDIA (OpenAI-compatible API).

    Lazily imports ``openai`` so this module imports fine without it. Falls
    back to the deterministic planner if the SDK or API key is unavailable, or
    if the model's response can't be parsed — the pipeline must never crash.
    """

    def __init__(self, fallback: Planner | None = None) -> None:
        self._fallback = fallback or RuleBasedPlanner()

    def classify(self, ticket: dict[str, Any], retrieved: list[dict[str, Any]]) -> Plan:
        from culprit.config import settings

        try:
            import json

            from openai import OpenAI
        except ImportError:
            return self._fallback.classify(ticket, retrieved)

        if not settings.nvidia_api_key:
            return self._fallback.classify(ticket, retrieved)

        context = "\n".join(
            f"- {r['title']} -> team={r['team']}, priority={r['priority']}" for r in retrieved
        )
        prompt = (
            "You triage IT support tickets. Given the ticket and similar resolved "
            "tickets, choose the owning team and a priority "
            f"({', '.join(p for p, _ in _PRIORITY_RULES)}).\n\n"
            f"Ticket: {ticket.get('title', '')}\n{ticket.get('description', '')}\n\n"
            f"Similar resolved tickets:\n{context or '(none)'}\n\n"
            'Respond with JSON only: {"team": str, "priority": str, "rationale": str}'
        )
        try:
            client = OpenAI(base_url=settings.nvidia_base_url, api_key=settings.nvidia_api_key)
            completion = client.chat.completions.create(
                model=settings.agent_model,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            data = json.loads(completion.choices[0].message.content)
            return Plan(
                team=data.get("team"),
                priority=data.get("priority"),
                planned_actions=["set_team", "set_priority"],
                rationale=data.get("rationale", ""),
            )
        except Exception:
            return self._fallback.classify(ticket, retrieved)


def default_planner(use_llm: bool = False) -> Planner:
    """Return the planner: deterministic by default, LLM-backed if requested."""
    return LLMPlanner() if use_llm else RuleBasedPlanner()


def plan_node(state: AgentState, planner: Planner | None = None) -> dict[str, Any]:
    """Produce the triage plan from the ticket and retrieved context."""
    planner = planner or default_planner()
    plan = planner.classify(state["ticket"], state.get("retrieved", []))
    return {"plan": plan.model_dump()}
