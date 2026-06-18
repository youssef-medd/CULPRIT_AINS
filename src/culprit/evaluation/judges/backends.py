"""Judge backends: the actual decision mechanism behind every judge.

* ``LLMJudgeBackend`` — the real, frontier mechanism. Renders the rubric-anchored
  prompt, randomizes the verdict-option order (a cheap position-bias mitigation),
  calls Anthropic, and parses the JSON verdict. Lazily imports ``anthropic`` and
  degrades to ``UNKNOWN`` (never crashes) on any failure.
* ``HeuristicJudgeBackend`` — a deterministic stand-in so the whole pipeline runs
  and is testable without an API key. It approximates the LLM's semantic checks
  with computable ones (e.g. retrieval relevance = do retrieved areas match the
  ticket's?). It is explicitly a degraded fallback, not the product.
"""

from __future__ import annotations

import json
import random
from string import Template
from typing import Any

from culprit.config import settings
from culprit.evaluation.judges.base import (
    ComponentJudgeRequest,
    EndToEndJudgeRequest,
    RawJudgment,
)
from culprit.schemas.evaluation import Evidence, Verdict
from culprit.schemas.trajectory import StepStatus, StepType

_EMPTY = (None, "", [], {})


def _verdict_options(rng: random.Random) -> str:
    """Randomized 'pass | fail' ordering to mitigate position bias."""
    options = ["pass", "fail"]
    rng.shuffle(options)
    return " | ".join(options)


# --------------------------------------------------------------------------- #
# LLM backend
# --------------------------------------------------------------------------- #
class LLMJudgeBackend:
    """Anthropic-backed judge. Non-deterministic; the real mechanism."""

    is_deterministic = False

    def __init__(self, model: str | None = None, seed: int | None = None) -> None:
        self.model = model or settings.judge_model
        self._rng = random.Random(seed)

    def _render(self, template: str, **fields: Any) -> str:
        return Template(template).safe_substitute(
            verdict_options=_verdict_options(self._rng), **fields
        )

    def _call(self, prompt: str, temperature: float) -> RawJudgment:
        try:
            import anthropic
        except ImportError:
            return RawJudgment(rationale="anthropic SDK not installed")
        if not settings.anthropic_api_key:
            return RawJudgment(rationale="no ANTHROPIC_API_KEY configured")
        try:
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            msg = client.messages.create(
                model=self.model,
                max_tokens=600,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return self._parse(msg.content[0].text)
        except Exception as exc:  # reliability: never crash the pipeline
            return RawJudgment(rationale=f"judge error: {exc}")

    @staticmethod
    def _parse(text: str) -> RawJudgment:
        try:
            start, end = text.index("{"), text.rindex("}") + 1
            data = json.loads(text[start:end])
            evidence = [Evidence(**e) for e in data.get("evidence", []) if isinstance(e, dict)]
            return RawJudgment(
                verdict=Verdict(str(data.get("verdict", "unknown")).lower()),
                score=float(data.get("score", 0.0)),
                failure_category=data.get("failure_category"),
                rationale=str(data.get("rationale", "")),
                evidence=evidence,
            )
        except Exception:
            return RawJudgment(rationale="unparseable judge response")

    def judge_component(
        self, request: ComponentJudgeRequest, temperature: float = 0.7
    ) -> RawJudgment:
        rubric = request.rubric
        criteria = (
            "\n".join(f"- {c.id}: {c.description}" for c in rubric.criteria) if rubric else "(none)"
        )
        categories = (
            "\n".join(f"- {c.id}: {c.description}" for c in rubric.failure_categories)
            if rubric
            else "(none)"
        )
        ref = request.reference
        ref_block = f"Reference (gold) to compare against:\n{json.dumps(ref)}" if ref else ""
        prompt = self._render(
            request.prompt_template,
            criteria=criteria,
            failure_categories=categories,
            context=json.dumps(request.context, default=str),
            reference_block=ref_block,
        )
        return self._call(prompt, temperature)

    def judge_end_to_end(
        self, request: EndToEndJudgeRequest, temperature: float = 0.7
    ) -> RawJudgment:
        task = request.task
        task_text = (
            "Required outputs: "
            + ", ".join(task.required_outputs)
            + "\nCriteria:\n"
            + "\n".join(f"- {c}" for c in task.success_criteria)
            if task
            else "(none)"
        )
        ref = request.reference
        ref_block = f"Reference (gold):\n{json.dumps(ref)}" if ref else ""
        prompt = self._render(
            request.prompt_template,
            task=task_text,
            context=json.dumps({"ticket": request.ticket, "outputs": request.outputs}, default=str),
            reference_block=ref_block,
        )
        return self._call(prompt, temperature)


# --------------------------------------------------------------------------- #
# Deterministic heuristic backend (offline / test fallback)
# --------------------------------------------------------------------------- #
class HeuristicJudgeBackend:
    """Deterministic approximation of the LLM judges. A degraded stand-in."""

    is_deterministic = True

    def judge_component(
        self, request: ComponentJudgeRequest, temperature: float = 0.0
    ) -> RawJudgment:
        dispatch = {
            StepType.RETRIEVAL: self._retrieval,
            StepType.PLANNING: self._planning,
            StepType.TOOL_EXECUTION: self._tool_execution,
            StepType.SYNTHESIS: self._synthesis,
        }
        handler = dispatch.get(request.step_type)
        return handler(request) if handler else RawJudgment(rationale="no heuristic for step type")

    # --- per-type heuristics ---
    def _retrieval(self, request: ComponentJudgeRequest) -> RawJudgment:
        ctx = request.context
        result = ctx.get("search_result") or {}
        retrieved = ctx.get("retrieved") or result.get("results") or []
        expected = (ctx.get("ticket") or {}).get("product_area")
        areas = sorted({r.get("product_area") for r in retrieved if r.get("product_area")})

        if result.get("filtered") is False:
            return RawJudgment(
                verdict=Verdict.FAIL,
                score=0.2,
                failure_category="no_filter_applied",
                rationale=f"Retrieval ran unfiltered and returned mixed areas {areas}.",
                evidence=[Evidence(field="tool.result.filtered", expected=True, actual=False)],
            )
        if expected and any(a != expected for a in areas):
            return RawJudgment(
                verdict=Verdict.FAIL,
                score=0.3,
                failure_category="irrelevant_context_retrieved",
                rationale=f"Retrieved tickets span {areas}, not the ticket's area '{expected}'.",
                evidence=[Evidence(field="tool.result", expected=f"{expected} tickets", actual=areas)],
            )
        if not retrieved:
            return RawJudgment(
                verdict=Verdict.FAIL,
                score=0.4,
                failure_category="insufficient_context_retrieved",
                rationale="Retrieval returned no tickets to ground routing.",
            )
        return RawJudgment(
            verdict=Verdict.PASS,
            score=0.9,
            rationale=f"Retrieved tickets are scoped to '{expected}' and relevant.",
        )

    def _planning(self, request: ComponentJudgeRequest) -> RawJudgment:
        plan = request.context.get("plan") or {}
        if not plan.get("team"):
            return RawJudgment(
                verdict=Verdict.FAIL,
                score=0.2,
                failure_category="wrong_team_selected",
                rationale="Plan did not select a team.",
                evidence=[Evidence(field="plan.team", expected="a team", actual=None)],
            )
        if not plan.get("priority"):
            return RawJudgment(
                verdict=Verdict.FAIL,
                score=0.3,
                failure_category="wrong_priority",
                rationale="Plan did not set a priority.",
            )
        return RawJudgment(
            verdict=Verdict.PASS,
            score=0.85,
            rationale=f"Plan routes to {plan['team']} at {plan['priority']}, following context.",
        )

    def _tool_execution(self, request: ComponentJudgeRequest) -> RawJudgment:
        step = request.step
        result = step.result if isinstance(step.result, dict) else {}
        if step.status == StepStatus.ERROR or result.get("status") == "error":
            reason = result.get("reason", "malformed_arguments")
            return RawJudgment(
                verdict=Verdict.FAIL,
                score=0.1,
                failure_category=reason,
                rationale=f"Tool call failed: {reason}.",
                evidence=[Evidence(field="tool.result.status", expected="ok", actual="error")],
            )
        args = step.action.arguments if step.action else {}
        if any(v in _EMPTY for v in args.values()):
            return RawJudgment(
                verdict=Verdict.FAIL,
                score=0.2,
                failure_category="missing_required_argument",
                rationale="A required tool argument was empty.",
            )
        return RawJudgment(verdict=Verdict.PASS, score=0.9, rationale="Tool call well-formed and ok.")

    def _synthesis(self, request: ComponentJudgeRequest) -> RawJudgment:
        ctx = request.context
        summary = (ctx.get("summary") or "").lower()
        record = ctx.get("jsm") or {}
        team = record.get("team")
        priority = record.get("priority")
        if team and team.lower() not in summary:
            return RawJudgment(
                verdict=Verdict.FAIL,
                score=0.3,
                failure_category="inconsistent_with_actions",
                rationale="Summary omits or contradicts the team that was set.",
                evidence=[Evidence(field="summary", expected=team, actual="(absent)")],
            )
        if priority and priority.lower() not in summary:
            return RawJudgment(
                verdict=Verdict.FAIL,
                score=0.4,
                failure_category="omitted_key_field",
                rationale="Summary omits the priority that was set.",
            )
        return RawJudgment(
            verdict=Verdict.PASS, score=0.9, rationale="Summary is grounded in the set team/priority."
        )

    def judge_end_to_end(
        self, request: EndToEndJudgeRequest, temperature: float = 0.0
    ) -> RawJudgment:
        outputs = request.outputs
        required = request.task.required_outputs if request.task else []
        missing = [f for f in required if outputs.get(f) in _EMPTY]
        if missing:
            return RawJudgment(
                verdict=Verdict.FAIL,
                score=0.2,
                rationale=f"Run is missing required outputs: {missing}.",
                evidence=[Evidence(field="outputs", expected=required, actual=sorted(outputs))],
            )
        expected_team = (request.reference or {}).get("expected_team")
        if expected_team and outputs.get("team") != expected_team:
            return RawJudgment(
                verdict=Verdict.FAIL,
                score=0.25,
                rationale=(
                    f"Ticket was routed to {outputs.get('team')} but should go to "
                    f"{expected_team} for its product area — a silent misroute."
                ),
                evidence=[
                    Evidence(field="outputs.team", expected=expected_team, actual=outputs.get("team"))
                ],
            )
        return RawJudgment(
            verdict=Verdict.PASS, score=0.9, rationale="Required outputs present and routing consistent."
        )


def default_backend() -> Any:
    """Return the LLM backend when a key is configured, else the heuristic one."""
    if settings.anthropic_api_key:
        try:
            import anthropic  # noqa: F401

            return LLMJudgeBackend()
        except ImportError:
            pass
    return HeuristicJudgeBackend()
