"""Verdict Generator (E4): turn an Attribution into an actionable report.

    from culprit.verdict import VerdictRenderer
    renderer = VerdictRenderer()
    report = renderer.render(attribution)   # structured + Markdown text
    renderer.write(attribution)             # -> data/outputs/<run_id>.{json,md}
"""

from culprit.verdict.renderer import VerdictRenderer, VerdictReport

__all__ = ["VerdictRenderer", "VerdictReport"]
