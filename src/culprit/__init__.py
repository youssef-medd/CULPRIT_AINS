"""Culprit — component-level failure attribution for non-deterministic AI agents.

When an agent run fails, Culprit names the component that caused it, backs the
verdict with cited evidence and a confidence score, and confirms the attribution
by counterfactual replay. This package is organized by subsystem:

    schemas/      shared OTel-GenAI-aligned types (Trajectory, verdicts, Attribution)
    contracts/    behavioral spec: per-step rubrics + ordering invariants
    agent/        the subject under test (JSM triage graph)
    recorder/     trajectory capture
    tagger/       step typing
    monitor/      online Shadow Contract Monitor
    evaluation/   LLM judges + self-consistency confidence + debate
    attribution/  decisive-step selection + counterfactual repair
    verdict/      human-readable reports
    drift/        cross-batch drift detection
    meta_eval/    judging the judges (fault injection + fuzzing + metrics)
"""

__version__ = "0.1.0"
