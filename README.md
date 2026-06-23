<p align="center">
  <img src="docs/images/culprit-banner.png" alt="Culprit" width="860">
</p>

# Culprit

**When your AI agent fails, Culprit names the component, proves it, and tells you how to fix it.**

Culprit is a continuous evaluation system for non-deterministic enterprise AI agents. It captures the full execution trajectory of an agent run, evaluates it at multiple levels with a panel of LLM judges, and — when a run fails — **attributes the failure to the specific component that caused it** (retrieval, planning, tool execution, or synthesis), backs that verdict with **evidence and a confidence score**, and **confirms the attribution by counterfactual replay**. A meta-evaluator then measures how often the attribution is *correct*.

> **AINS Hackathon 2026** · Use Case 1 — Continuous Evaluation for Non-Deterministic AI Agents · **Scenario C — Component-Level Failure Attribution**
> Evaluation target (scope-disciplined): a single **Atlassian Jira Service Management (JSM) ticket-triage agent**.

---

## 1. The problem

Enterprise teams deploy agents that don't behave deterministically: the same JSM ticket can produce different tool calls and different routing on two runs. This breaks the usual safety net in three ways:

1. **Pass/fail unit tests don't apply** — there is no exact output to match against.
2. **Silent failures** — an agent can call all the right-*looking* tools, finish with no error, and still misroute a ticket. You find out after the damage is done.
3. **Useless failure signal** — when it does fail, "task failed" tells an engineer *nothing about which step to fix*: was it retrieval, planning, the tool parameters, or the final summary?

Inside Atlassian this gap is explicitly documented: there is no mechanism today to detect that an agent has drifted from its spec, or to attribute a failed run to a component. Culprit fills exactly that gap.

## 2. Why this needs AI (it is the mechanism, not a feature)

Remove the model and Culprit ceases to exist. There is no rule that decides "retrieval returned irrelevant context" or "the final summary asserts a field that was never retrieved" — these are semantic judgments over unstructured reasoning traces and tool I/O. The core mechanism is a **panel of LLM judges evaluating against behavioral contracts**, plus a **meta-evaluator that measures whether those judges are right**. It is not keyword matching, not template filling, and not a wrapper around an existing Atlassian feature.

## 3. Design philosophy: narrow and deep

Automated failure attribution is a **frontier research problem**, not a solved one. On the `Who&When` benchmark the best automated method reaches only ~53.5% at naming the responsible component and ~14.2% at pinpointing the failing step; on `TRAIL` the best frontier model scores ~11% at trace debugging, and accuracy *drops* as the trace gets longer. Two design laws follow directly from that literature and shape every decision below:

1. **Constrain the domain.** General-purpose trace debugging sits at ~11–14%. We win accuracy by *not* being general — one fixed agent, fixed step types, explicit per-step contracts — and we report the resulting accuracy honestly.
2. **Don't judge the whole trace at once.** Because accuracy is anti-correlated with context length, Culprit uses **focused per-step judges** rather than one monolithic whole-trace judge, and **confirms each attribution causally** (replay) instead of trusting a single LLM opinion.

Capture and tracing are commoditized (LangSmith, Phoenix, Braintrust). Culprit's defensible contribution is the stack none of them ship as a product: **multi-level judging → first-decisive-step attribution → counterfactual confirmation → meta-evaluation of the judge.**

## 4. System design

### 4.1 Architecture

![Culprit system architecture](docs/images/architecture.png)

The **courtroom metaphor** keeps the whole system intuitive and maps 1:1 to it: behavioral **contracts** are the statute; the **judges** are a panel; **evidence** is cited trajectory fields; the **verdict** is the report; **confidence** is jury agreement; **counterfactual replay** re-enacts the run to confirm the culprit; the **meta-evaluator** is the appeals court that audits the judges.

### 4.2 Components (each has one job)

- **JSM Triage Agent** — the non-deterministic system being evaluated; produces a multi-step trajectory with natural failure points. Kept deliberately simple — it is not the product.
- **Trajectory Recorder** — captures every step (reasoning, tool, parameters, result, latency, status) into an OTel-GenAI-aligned, inspectable `Trajectory`, with a per-step context snapshot. No AI — pure instrumentation.
- **Step Tagger** — labels each step with a type (rule-based on span/tool name, with a cheap-LLM fallback) so judges and attribution can localize.
- **Contract Store** — the behavioral spec: per-step rubrics, the task-success definition (what "correct" means), and **ordering/structural invariants**, as small versioned YAML files. The contracts feed *both* evaluation layers below.
- **Shadow Contract Monitor (online)** — a deterministic **runtime-verification** state machine compiled from the contracts' ordering invariants (e.g. *a relevant retrieval must precede planning; set_team must precede set_priority; the chosen tool must be capable*). It runs **in parallel** with the live agent and fires a **mid-flight divergence alert** the moment the trajectory violates an invariant — the *online* arm of drift/non-determinism. It checks the **sequence of actions, not the exact text**, so legitimately different valid paths don't trip it.
- **Component Judges** — per-step LLM judges scoring each step against its rubric with **focused context**, returning pass/fail + score + cited evidence. The *semantic* layer: they catch what a state machine can't (irrelevant context, hallucinated grounding).
- **End-to-End Judge** — a task-level success verdict; the second, distinct evaluation level.
- **Self-Consistency Confidence (+ debate escalation)** — k-samples each judge; agreement becomes the confidence. On genuine disagreement, a lane runs a short **multi-agent debate** (pass-stance vs fail-stance, adjudicated by a Senior Judge) to resolve it; anything still unresolved escalates to a human. Handles non-determinism *and* cuts the review queue without erasing the uncertainty signal.
- **Decisive-Step Selector** — picks the *earliest* high-confidence violation as the primary suspect (the Who&When decisive-step definition). A structural violation from the Shadow Monitor is a cheap, high-precision early signal here.
- **Minimal Counterfactual Repair** — re-runs the agent from the suspect step and searches for the **smallest single-variable change that flips the outcome to success**, reporting a *validated* repair with a Causal Responsibility Score (CRS). An outcome flip *causally confirms* the attribution; the minimal edit makes the fix precise ("change this one parameter"). Falls back to coarse-correction replay if no small edit flips it.
- **Verdict Generator** — renders the confirmed attribution into a structured, human-readable, actionable report — for every run, including passing ones.
- **Synthetic Failure Generator + Trajectory Mutation Engine** — beyond hand-written faults, a **structure-aware fuzzer** programmatically mutates known-good trajectories (semantic noise, truncated tool results, reordered retrieval blocks, parameter perturbation) to generate a large *labeled* corpus and a **Fuzzing & Resilience Report**. This manufactures the ground truth the Meta-Evaluator needs.
- **Meta-Evaluator** — measures how often Culprit attributes correctly across the labeled + fuzzed corpus (the proof the evaluator works).
- **Drift Monitor** — flags behavioral distribution shifts *across run batches* over time (PSI/KL) — complementary to the Shadow Monitor's *within-run* divergence.
- **Dashboard (interactive DAG)** — the explainability surface: the trajectory rendered as a directed graph, the decisive node pulsing red, click-to-expand showing the violated contract, evidence, confidence, and the validated minimal repair. A *decoupled* layer that consumes the core's JSON.

### 4.3 Data flow

![Culprit data flow](docs/images/data_flow.png)

### 4.4 Runtime sequence

![Culprit runtime sequence](docs/images/runtime_sequence.png)

### 4.5 The attribution algorithm

```text
attribute(trajectory, verdicts, tau):
    if end_to_end(verdicts) == "pass":
        return Attribution(verdict="pass")          # a PASS run still gets a report (E4)

    # earliest high-confidence component violation = decisive suspect (Who&When)
    suspects = [v for v in component_verdicts(verdicts)
                if v.verdict == "fail" and v.confidence >= tau]
    suspects.sort(by=step_index)

    for s in suspects:                              # causal confirmation via MINIMAL repair
        edits = propose_minimal_edits(s, k=4)       # lightweight LLM: one variable each
        for e in sorted(edits, by=edit_size):       # smallest change first
            if replay_from(trajectory, s.step_id, edit=e) == "task_succeeded":
                return Attribution(decisive=s, confirmed=True,
                                   repair=e, crs=causal_responsibility(s), fix=...)
        # fallback: coarse corrected-I/O replay so E3 is never at risk
        if replay_from(trajectory, s.step_id, correction=gold_or_proposed(s)) == "task_succeeded":
            return Attribution(decisive=s, confirmed=True, fix=...)

    return Attribution(decisive=suspects[0], confirmed=False, alternatives=suspects[1:])
```

The **earliest-violation rule** stops Culprit from blaming a downstream symptom when an upstream step poisoned its input; the **counterfactual replay** turns a correlational judgment into a demonstrable causal claim.

### 4.6 How the judges stay honest

LLM judges have documented position, verbosity, and self-enhancement biases (since MT-Bench). Culprit mitigates each cheaply: **rubric-anchored** prompts tied to a written contract, **reference-based** scoring where a gold answer exists, **randomized option order**, and **self-consistency** (k samples → agreement = confidence). Low-confidence verdicts are surfaced for human review rather than asserted — which is also the self-evaluation bonus.

### 4.7 Proving the evaluator works ("judging the judges")

The hardest question a judge can ask is *"how do you know your judge is right?"* — and most teams have no answer. Culprit manufactures its own ground truth: a **fault injector** deterministically corrupts a known-good trajectory into a **labeled** failing one. Running Culprit over many labeled cases yields **attribution accuracy, per-category precision/recall/F1, and step-localization accuracy**, benchmarked against the published ~14.2% step-localization SOTA. This single mechanism wins the Evaluation dimension, earns the self-evaluation bonus, and produces the labels that make any metric possible.

### 4.8 Schemas

Trajectory, evaluation, and attribution are defined as OTel-GenAI-aligned typed schemas (pydantic models) under `src/culprit/schemas/`, and the behavioral contracts (rubrics + ordering invariants) live under `src/culprit/contracts/`. The attribution payload — the system's primary output — looks like:

```json
{
  "run_id": "run_2026_0617_017",
  "end_to_end_verdict": "fail",
  "decisive_step_id": "step_00",
  "decisive_step_type": "retrieval",
  "failure_category": "irrelevant_context_retrieved",
  "why": "Retrieval omitted the product_area filter and returned unrelated tickets; the planner then routed the VPN ticket to the wrong team. Every tool call returned ok, so no error fired - a silent failure.",
  "evidence": [
    { "field": "action.arguments.product_area", "expected": "networking", "actual": null },
    { "field": "tool.result", "expected": "VPN / networking tickets", "actual": "printer, email tickets" }
  ],
  "confidence": 0.88,
  "counterfactual": { "performed": true, "result": "task_succeeded", "confirms_attribution": true },
  "recommended_fix": "Populate product_area in the retrieval call and add a relevance re-ranker."
}
```

### 4.9 Two-layer evaluation: deterministic monitor + semantic judges

Culprit evaluates on two complementary layers, a design borrowed from **runtime verification of LLM agents**, where the field's central lesson is to monitor the *sequence of actions and ordering invariants* rather than exact text — which is exactly what makes a deterministic check compatible with a non-deterministic agent:

- **Deterministic layer — Shadow Contract Monitor.** Each contract's ordering invariants compile into a small state machine (a "digital twin" of intended behavior) that runs *online*, in parallel with the agent. It catches *structural* faults instantly and cheaply — wrong tool order, a missing step, an incapable tool, accessing a field before it was retrieved — and raises a **mid-flight divergence alert** before any LLM judge runs. Because it checks invariants over actions, not text, different valid paths don't trip it.
- **Semantic layer — LLM judges.** These catch what no state machine can express — *was the retrieved context actually relevant? is the summary grounded?* — with focused context and self-consistency confidence.

Two protocol contributions come out of this: the offline **component-attribution event** and an **online divergence signal** for the same OTel-aligned trace.

To *prove* the whole stack, Culprit doesn't stop at a handful of hand-written faults. A **Trajectory Mutation Engine** (structure-aware fuzzing, in the lineage of classic mutation/coverage fuzzing such as DeepMutation and TensorFuzz, extended to agent trajectories) programmatically mutates known-good trajectories into hundreds of *labeled* failing ones, mapping the agent's exact breaking points and measuring how accurately attribution isolates each injected bug — surfaced as a **Fuzzing & Resilience Report**. Crucially the ground truth comes from the *injection*, not from an LLM-written oracle.

### 4.10 Precision, uncertainty & explainability

Three further enhancements, each *deepening an existing component* (no new subsystem):

- **Minimal Counterfactual Repair (CRS).** The attribution engine doesn't just confirm the culprit — it searches for the *smallest single-variable change that flips the outcome to success* and reports it as a validated repair with a Causal Responsibility Score we define. Grounded in the counterfactual-explanation minimality principle (Wachter et al., 2017) and intervention-based causal analysis (Pearl's ladder of causation). Turns "retrieval was wrong" into "change this one parameter and it passes."
- **Multi-agent debate for uncertain verdicts.** When judges genuinely disagree, a short pass-vs-fail debate adjudicated by a Senior Judge resolves it before falling back to human escalation — cutting the review queue while *preserving* the human-in-the-loop for anything still unresolved (Du et al., 2023; ChatEval, 2023; Irving et al., 2018).
- **Interactive DAG dashboard.** The trajectory is rendered as a graph; the decisive node pulses red; clicking it reveals the violated contract, evidence, confidence, and the validated minimal repair — directly serving the Explainability dimension. The dashboard is a *decoupled* layer over the core's JSON.

## 5. Acceptance-criteria coverage

Each criterion from the brief is mapped to a component and an implementation.

| # | Criterion | Priority | Component | Implementation |
|---|---|---|---|---|
| E1 | Trajectory capture works | **Must** | Recorder | LangGraph callbacks emit OTel-GenAI spans → typed `Trajectory` in SQLite/JSON |
| E2 | Multi-level evaluation | **Must** | Judges + contracts | Per-step component judges (focused context) + an end-to-end judge; rubric-anchored, no exact-match |
| E3 | Failure attribution | **Must** | Attribution Engine | Earliest high-confidence violation = decisive step, confirmed by **minimal counterfactual repair** (smallest change that flips the outcome → validated fix + CRS) |
| E4 | Human-readable verdict | **Must** | Verdict Generator | Template renders the Attribution into a report — for every run incl. PASS |
| E5 | Drift detection | Should | Shadow Monitor + Drift Monitor | *Online* within-run divergence alerts (runtime-verification state machine) **and** *batch* PSI/KL across run batches — two timescales |
| E6 | Non-determinism addressed | Should | Self-Consistency Confidence + Shadow Monitor | k-sample judges (agreement = confidence) for semantics, with **debate** resolving genuine disagreements before human escalation; invariant-over-actions checking for structure — both robust to different valid paths |
| E7 | Evaluation of the evaluator | Should | Meta-Evaluator + Mutation Engine | Inject + **fuzz** labeled faults (hundreds of variations) → attribution accuracy / P / R / F1 / step-localization + resilience report |
| G1 | AI is the mechanism | Gating | whole system | Judging + attribution are irreducibly semantic |
| G2 | Actionable structured output | Gating | Verdict Generator | Evidence + confidence + recommended fix |
| G3 | Beyond retrieval | Gating | Judges + Attribution | Multi-level classification + attribution + drift |
| G4 | Explainability | Gating | Verdict + interactive DAG dashboard | Cited evidence + confidence + decision trace + a red decisive node with click-to-expand contract/evidence/validated repair |
| G5 | Metric on a test set | Gating | Meta-Evaluator | Metrics on a synthetic labeled set |
| NF1 | Responsiveness | Non-func | (design) | Latency budget + gating (deep path only on failure) |
| NF2 | Reliability | Non-func | (design) | Degraded modes: judge failure → low-confidence fallback; missing fields flagged, no crash |
| NF3 | Scalability mindset | Non-func | (design) | Async judge pool; offline meta-eval; gating keeps cost ∝ failure-rate |

## 6. Bonus points — all four targeted

| Bonus | How Culprit earns it |
|---|---|
| **Protocol gap addressed & documented** | OTel GenAI standardizes `invoke_agent` / `execute_tool` spans and an evaluation event, but defines **no component-attribution event** and **no online divergence event**. Culprit specifies both and aligns them to OTel (schemas under `src/culprit/contracts/`). |
| **Self-evaluation** | Self-consistency confidence, **multi-agent debate** to resolve uncertain verdicts, and the meta-evaluator (proven on a fuzzed, labeled corpus) — together they surface and resolve low-confidence verdicts while still escalating the genuinely ambiguous ones to humans. |
| **Open contribution** | The failure taxonomy, contract schema, and meta-eval design ship as reusable artifacts under MIT (`src/culprit/contracts/`). |
| **Real enterprise validation** | *Aspirational / in progress:* recruiting ≥1 enterprise engineer / AI-platform owner to run the prototype on their own JSM-style tickets and log structured feedback on attribution usefulness. |

## 7. Gap analysis vs. the state of the art

Capture and tracing are commoditized; Culprit is positioned squarely on what these tools *don't* ship.

| Tool | Strength | What it does NOT give you |
|---|---|---|
| LangSmith | Tracing, datasets, LLM-as-judge scoring | First-decisive-step **attribution**; counterfactual confirmation; meta-eval of the judge |
| Arize Phoenix | OSS tracing, span-level eval | Causal/counterfactual attribution; "which component caused it" as a verdict |
| Braintrust | Scorers, eval datasets, regression tracking | Component attribution; replay-based confirmation |
| AgentOps | Session/step tracking, cost/latency | Principled multi-level eval + attribution engine |
| OpenTelemetry GenAI | Standard spans + an evaluation event | A component-**attribution** event (the gap Culprit fills) |
| Datadog LLM Obs / WhyLabs | Monitoring, drift at scale | Evidence-backed root-cause + eval-of-evaluator |

## 8. Failure modes of the design (and how we handle them)

Naming where the system can break is part of the engineering, not an afterthought.

| Failure mode | Why it happens | Mitigation |
|---|---|---|
| The judge is simply wrong | LLM evaluation is noisy/biased | Meta-eval **quantifies** the error; rubric anchoring + self-consistency reduce it |
| Over-attribution (everything "fails") | Contracts too strict | Calibrate threshold τ on the synthetic set; report calibration |
| Cascading false blame | A downstream step fails only because an upstream step poisoned its input | Earliest-decisive-violation rule + counterfactual confirmation |
| Symptom ≠ root cause | Correlation-only judging | Counterfactual replay: fixing the suspect must flip the outcome |
| Cost / latency blowup | N judges × k samples on every run | Gate the deep path on `fail OR confidence<τ`; cheap model for tagging; the Shadow Monitor is a cheap deterministic pre-filter |
| Shadow Monitor false alerts | Invariants too strict; a valid alternative path looks like divergence | Invariants are deliberately *minimal and structural* (ordering/capability), never exact-path; alerts are signals into attribution, not hard blocks; tuned on the fuzzed corpus |
| Shadow Monitor blind spots | Semantic faults can't be expressed as invariants | By design it only covers structural categories; the LLM judges own the semantic ones — the two layers are complementary, not redundant |
| Debate converges confidently-wrong | Persuasive-but-wrong consensus / sycophancy in LLM debate | Debate never erases the uncertainty signal: unresolved or low-confidence debates still escalate to a human; debate triggers only on genuine disagreement |
| Minimal repair doesn't generalize | A small edit that flips *this* run may not fix all tickets | Reported as a *validated local* fix with a CRS, not a global patch; falls back to coarse-correction replay if no minimal edit flips it |
| Demo flakiness | A non-deterministic agent live | Run on recorded fixtures / seeded replay (and frame determinism as a feature) |

## 9. Non-functional design

- **Responsiveness (NF1).** Indicative budget (to be validated): a passing run ≈ 10–14 s (tagging < 1 s, parallel k-sampled component judges ≈ 6–10 s, end-to-end judge ≈ 2–3 s); a failing run adds ≈ 8–12 s for counterfactual replay. **Gating** runs the expensive deep path only on failed/low-confidence runs.
- **Reliability (NF2).** A judge timeout retries once, then emits `unknown` at confidence 0 and flags for review — the pipeline never crashes. Missing/empty ticket fields are treated as signal (a missing `component` is itself attributable), not a crash. A failed replay falls back to correlation-based attribution so the E3 Must still holds.
- **Scalability (NF3).** Judges are independent → an async pool scales horizontally. Gating means deep-path cost scales with the *failure rate*, not the run rate, so it grows sub-linearly at 10× volume. Meta-eval runs offline/batch, decoupled from the online path. Storage moves SQLite → Postgres; trajectories are append-only, partitioned by day.

## 10. Repository layout

```
CULPRIT_AINS/
├── README.md
├── LICENSE
├── pyproject.toml                  # packaging + core/optional dependency groups
├── .env.example                    # NVIDIA_API_KEY, models, tau, paths
├── docs/images/                    # architecture, data-flow, runtime-sequence diagrams
├── src/culprit/
│   ├── config.py                   # env-driven settings singleton
│   ├── run.py                      # end-to-end pipeline + CLI (python -m culprit.run)
│   ├── __main__.py                 # python -m culprit
│   ├── schemas/                    # OTel-GenAI-aligned types: trajectory / evaluation / attribution
│   ├── contracts/                  # the eval spec: rubrics/ + invariants/ + task_success.yaml + loader
│   ├── agent/                      # subject under test: JSM triage graph
│   │   ├── graph.py                #   retrieve → plan → act → synthesize (LangGraph)
│   │   ├── nodes/                  #   one file per node (pluggable rule/LLM brains)
│   │   └── tools/                  #   mocked JSM tools + capability registry
│   ├── recorder/                   # E1: callback capture → trajectory_builder → SQLite store
│   ├── tagger/                     # step typing (rules + cheap-LLM fallback)
│   ├── monitor/                    # E5 (online): Shadow Contract Monitor (compiler + state machine)
│   ├── evaluation/                 # E2/E6: judges/ (+ LLM & heuristic backends), confidence, debate, prompts/
│   ├── attribution/                # E3: selector + counterfactual + crs + engine
│   ├── verdict/                    # E4: renderer + Jinja2 templates/
│   ├── drift/                      # E5 (batch): PSI/KL detector
│   └── meta_eval/                  # E7: injector + mutation_engine + scorer + report (python -m culprit.meta_eval)
├── data/
│   ├── synthetic/                  # tickets.jsonl + recorded trajectories (fixtures)
│   └── outputs/                    # generated verdicts (JSON + Markdown) and meta-eval report
├── ui/                             # Next.js 16 dashboard (decoupled over the core's JSON)
│   ├── app/                        #   Next.js 16 App Router
│   ├── components/                 #   React components (culprit/ + ui/)
│   ├── lib/                        #   Data layer, types, constants
│   ├── data/                       #   culprit-data.json — generated by tools/gen_demo_data.py
│   └── public/                     #   Static assets (favicon, placeholders)
└── tests/                          # pytest suite mirroring src/culprit (56 tests)
```

## 11. Setup & usage

**Requirements:** Python 3.11+. An LLM API key is **optional** — every LLM-backed component (agent planner, judges, summarizer, tagger) ships with a deterministic fallback, so the full pipeline runs and the test suite passes with no key. That makes runs reproducible for fixtures, CI, and demos; set a key to switch to a real model.

```bash
git clone https://github.com/youssef-medd/CULPRIT_AINS.git
cd CULPRIT_AINS
python -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\activate

pip install -e .                          # core — runs the whole pipeline deterministically
pip install -e ".[agent,dev]"             # optional — real LLM agent/judges, tests

# Optional: switch the agent + judges from the deterministic stand-in to a real model.
export NVIDIA_API_KEY=nvapi-...
```

```bash
# Subject agent + full evaluation pipeline over the synthetic tickets
python -m culprit.run --tickets data/synthetic/tickets.jsonl

# "Judging the judges": inject + fuzz labeled faults, report attribution accuracy / P / R / F1
python -m culprit.meta_eval

# Generate demo data for the dashboard (Python, run from repo root)
python tools/gen_demo_data.py

# Interactive dashboard (requires Node.js 20+)
cd ui && npm install && npm run dev

# Test suite
pytest
```

Each command writes structured verdicts (JSON) and human-readable reports (Markdown) to `data/outputs/`; the dashboard renders the trajectory as an interactive graph with the decisive node highlighted.

## 12. Technical stack (chosen, justified)

- **Orchestration:** LangGraph — an explicit node/edge graph makes step boundaries (and therefore step-level attribution) first-class.
- **Subject agent:** a 4-node JSM triage graph — `Retrieve similar tickets → Plan (classify + choose actions) → Act (set team/priority via mocked JSM tools) → Synthesize summary`. Mocked tools keep runs deterministic and side-effect-free (no live Jira writes).
- **Judges:** LLM-as-judge, rubric-anchored and reference-based, with randomized option order and self-consistency sampling.
- **Capture:** framework callbacks emitting OpenTelemetry GenAI-aligned spans.
- **Storage:** SQLite for runs (Postgres at scale).
- **UI (decoupled):** an interactive **dashboard** (overview, runs & attribution, meta-eval, drift tabs), built with **Next.js 16** (App Router, Turbopack), **Tailwind CSS v4**, **shadcn/ui**, and **Recharts**. The data layer (`lib/data.ts`) imports a single JSON file (`data/culprit-data.json`) generated by `tools/gen_demo_data.py` — the evaluation engine never depends on the web framework, so the UI is swappable without touching the core.

## 13. Research foundation

- **Who&When** — Zhang et al., ICML 2025 (arXiv:2505.00212). Formalizes automated failure attribution; defines the **decisive step** = the earliest mistake whose correction flips failure→success. Adopted directly.
- **TRAIL** — Patronus AI, 2025 (arXiv:2505.08638). Error taxonomy; accuracy anti-correlated with context length → justifies focused per-step judges.
- **Agent-as-a-Judge** — Zhuge et al., 2024 (arXiv:2410.10934). Step-level feedback beats outcome-only → justifies multi-level evaluation.
- **MAST** — Cemri et al., NeurIPS 2025 (arXiv:2503.13657). 14 empirical failure modes; many failures stem from system design, not model limits → attribution-then-fix is the right loop.
- **Causal / counterfactual analysis** — intervention beats correlation (Pearl's ladder of causation; counterfactual reasoning) → backs the replay/repair step.
- **Self-Consistency** — Wang et al., 2022; **G-Eval** — Liu et al., 2023; **LLM-as-judge biases** — Zheng et al., 2023 (MT-Bench).
- **OpenTelemetry GenAI semantic conventions** (v1.4x) — the interoperable schema baseline and the documented gap Culprit fills.
- **Runtime verification of agents** — grounds the Shadow Contract Monitor: monitor the action sequence and ordering invariants independent of exact textual output, so legitimately different valid paths don't trip the monitor while genuine structural violations do.
- **Adversarial testing** — DeepMutation (Ma et al., ISSRE 2018) and TensorFuzz (Odena et al., ICML 2019) ground the Trajectory Mutation Engine; Culprit extends structure-aware mutation to agent *trajectories*.
- **Minimal counterfactual repair** — the minimality principle from counterfactual explanations (Wachter, Mittelstadt & Russell, 2017), combined with intervention-based causal reasoning (Pearl), motivates the Causal Responsibility Score.
- **Multi-agent debate** — Du et al. (2023); ChatEval (Chan et al., 2023); AI safety via debate (Irving, Christiano & Amodei, 2018).

## 14. Status & limitations

**Implementation status.** All components above are implemented, wired into one pipeline (`python -m culprit.run`), and covered by a passing `pytest` suite. The agent, judges, summarizer, and tagger run on a real LLM when `NVIDIA_API_KEY` is set, and on a deterministic stand-in otherwise — so the system is fully runnable and reproducible with no key.

Honest open risks: counterfactual replay is the highest-risk component and is designed to **degrade gracefully** to correlation-based attribution if no replay flips the outcome. The meta-evaluator's headline numbers on the bundled corpus are produced by the **deterministic heuristic judge backend over a small, by-construction-labeled set** — they show the attribution and meta-evaluation machinery is correct end-to-end, *not* that the LLM judges hit that accuracy in the wild (run with a key and a noisier corpus for the realistic regime). Reported accuracy is on a **deliberately constrained** domain (a single JSM triage agent), which is the point of the scoping decision — general-purpose trace debugging sits at ~11–14%, and Culprit trades breadth for measurable accuracy.

**License:** MIT (see [`LICENSE`](LICENSE)).
