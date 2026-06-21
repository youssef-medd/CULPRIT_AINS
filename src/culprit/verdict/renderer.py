"""Verdict Generator (E4): render an Attribution into a human-readable report.

Produces, for *every* run including passes, both artifacts:

* the **structured** attribution JSON (the machine-readable, actionable payload), and
* a **human-readable** Markdown report rendered from a Jinja2 template.

Jinja2 is used when present; a plain-text fallback keeps the renderer working
without it so a report is always produced.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from culprit.config import settings
from culprit.schemas.attribution import Attribution

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


class VerdictReport(BaseModel):
    """A rendered verdict: the structured attribution plus its text report."""

    run_id: str
    verdict: str
    text: str
    attribution: Attribution


class VerdictRenderer:
    """Renders attributions to Markdown and writes them alongside their JSON."""

    def __init__(self, templates_dir: Path | None = None) -> None:
        self.templates_dir = templates_dir or TEMPLATES_DIR
        self._env = self._make_env()

    def _make_env(self) -> Any:
        try:
            from jinja2 import Environment, FileSystemLoader, select_autoescape

            return Environment(
                loader=FileSystemLoader(str(self.templates_dir)),
                autoescape=select_autoescape(default_for_string=True, default=True),
                trim_blocks=False,
                lstrip_blocks=False,
            )
        except ImportError:
            return None

    def render_text(self, attribution: Attribution) -> str:
        """Render the Markdown report for an attribution."""
        if self._env is not None:
            name = "pass.jinja2" if attribution.is_pass else "fail.jinja2"
            return str(self._env.get_template(name).render(a=attribution))
        return _fallback_text(attribution)

    def render(self, attribution: Attribution) -> VerdictReport:
        """Build a full VerdictReport (structured + text)."""
        return VerdictReport(
            run_id=attribution.run_id,
            verdict=attribution.end_to_end_verdict.value,
            text=self.render_text(attribution),
            attribution=attribution,
        )

    def write(self, attribution: Attribution, output_dir: Path | None = None) -> dict[str, Path]:
        """Write the JSON payload and Markdown report; return their paths."""
        out = output_dir or settings.output_dir
        out.mkdir(parents=True, exist_ok=True)
        json_path = out / f"{attribution.run_id}.json"
        md_path = out / f"{attribution.run_id}.md"
        json_path.write_text(attribution.model_dump_json(indent=2), encoding="utf-8")
        md_path.write_text(self.render_text(attribution), encoding="utf-8")
        return {"json": json_path, "markdown": md_path}


def _fallback_text(a: Attribution) -> str:
    """Minimal plain-text report used when Jinja2 is unavailable."""
    if a.is_pass:
        return (
            f"Culprit Verdict — {a.run_id}\n"
            f"Result: PASS (confidence {a.confidence:.2f})\n{a.why or ''}"
        )
    lines = [
        f"Culprit Verdict — {a.run_id}",
        "Result: FAIL",
        f"Decisive step: {a.decisive_step_id} ({a.decisive_step_type})",
        f"Failure category: {a.failure_category}",
        f"Confidence: {a.confidence:.2f} | CRS: {a.crs}",
        f"Why: {a.why}",
        f"Confirmed by counterfactual: {a.counterfactual.confirms_attribution}",
        f"Recommended fix: {a.recommended_fix}",
    ]
    return "\n".join(lines)
