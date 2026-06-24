# Data Description

This document satisfies the AINS final-submission requirement for a data
description: *sources used, formats, key fields, quality notes, and sensitivity
handling.* Culprit uses **no real customer data**. Every input is synthetic and
generated in-repo so runs are reproducible and contain no PII.

## 1. Sources

| Dataset | Location | Origin | Role |
|---|---|---|---|
| **Synthetic JSM tickets** | `data/synthetic/tickets.jsonl` | Hand-authored | The input the subject agent triages. |
| **Behavioral contracts** | `src/culprit/contracts/` | Hand-authored | The evaluation spec (rubrics, invariants, task-success). |
| **Recorded trajectories** | `data/synthetic/trajectories/`, `data/culprit.db` | Derived (the agent runs) | The execution traces the judges evaluate. |
| **Labeled fault corpus** | Generated at runtime by the meta-evaluator | Derived (injector + fuzzer) | Ground truth for "judging the judges". |
| **Verdicts & reports** | `data/outputs/` | Derived (the pipeline) | Structured attributions (JSON) + human-readable reports (Markdown). |

Only the first two are authored by hand; everything else is **derived
deterministically** from them by the pipeline, so the corpus is fully
regenerable from a clean clone.

## 2. Formats

- **Tickets** — JSON Lines (`.jsonl`), one ticket object per line.
- **Contracts** — YAML (versioned, small, human-editable).
- **Trajectories / evaluations / attributions** — OTel-GenAI-aligned Pydantic
  models (`src/culprit/schemas/`), serialized to JSON and SQLite.
- **Reports** — Markdown rendered from the attribution payload.

## 3. Key fields

### Ticket (`data/synthetic/tickets.jsonl`)
| Field | Type | Notes |
|---|---|---|
| `id` | string | Ticket key, e.g. `JSM-101`. |
| `title` | string | Short summary. |
| `description` | string | Free-text body the agent reasons over. |
| `product_area` | string \| null | Ground-truth routing domain: `networking`, `printing`, `email`, `identity`, `software`. **Nullable by design** (see quality notes). |
| `reporter` | string | Fabricated first name (not a real person). |

### Attribution payload (primary output — `data/outputs/<run_id>.json`)
`run_id`, `end_to_end_verdict`, `decisive_step_id`, `decisive_step_type`,
`failure_category`, `why`, `evidence[]` (field / expected / actual),
`confidence`, `counterfactual` (performed / result / confirms_attribution),
`recommended_fix`. The schema is documented in README §4.8.

## 4. Quality notes

- **Small, by-construction-labeled set.** 7 tickets spanning 5 product areas.
  The set is intentionally small and clean so the meta-evaluator has unambiguous
  ground truth — it proves the attribution machinery is correct end-to-end, not
  that the LLM judges hit that accuracy on noisy production data (README §14).
- **One deliberately ambiguous ticket.** `JSM-107` has `product_area: null` and a
  vague description ("something is broken"). It exercises the reliability path:
  tickets without a well-specified area are *skipped* by the fuzzer (their
  "correct" routing is undefined), and the agent must not crash on missing
  fields — a missing field is treated as signal, not an error.
- **Coherent fault injection.** The labeled fault corpus is produced by
  corrupting known-good trajectories (e.g. unfiltered retrieval, wrong team,
  missing tool argument, inconsistent summary). The label comes from the
  *injection*, never from an LLM oracle, so ground truth is exact.
- **Backend mode is explicit.** Every run prints whether it used the real LLM
  judges or the deterministic stand-in, so reproducibility-mode output is never
  mistaken for the AI evaluation path.

## 5. Sensitivity handling

- **No real data, no PII.** All tickets are fabricated; reporter names are
  generic first names with no association to real individuals.
- **No live side effects.** The JSM tools are mocked — no ticket is ever created
  or modified in a real Atlassian instance.
- **Secrets stay out of the repo and image.** `NVIDIA_API_KEY` is read from a
  gitignored `.env`; `.dockerignore` excludes `.env` so it is never baked into a
  container image.
- **Scaling to real data.** On a real JSM instance the same schema applies;
  PII would be confined to the ticket text. The evaluation never needs to store
  ticket bodies beyond the trajectory, and trajectories are append-only and
  partitionable by day for retention control (README §9).
