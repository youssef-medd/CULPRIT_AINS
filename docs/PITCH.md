# Pitch Deck Outline — Culprit

15 slides, mapped to the required elements (§1.5.2) and the judging weights
(Engineering Depth 50% · Prototype Quality 25% · Explainability 15% ·
Evaluation 10%). Build these in your slide tool of choice; speaker notes in
italics.

---

**1 — Title**
Culprit. *"When your AI agent fails, Culprit names the component, proves it, and
tells you how to fix it."* AINS 2026 · Use Case 1 · Scenario C. Team + logo.

**2 — The problem** *(sets up Engineering Depth)*
Enterprises deploy non-deterministic agents. Same JSM ticket → different tool
calls each run. Three breakages: pass/fail tests don't apply; **silent
failures** (all tools "ok", ticket still misrouted); and "task failed" tells an
engineer *nothing about which step to fix*.

**3 — Why this is a real Atlassian gap**
No mechanism today to detect an agent drifted from spec, or to attribute a
failed run to a component. Capture/tracing is commoditized (LangSmith, Phoenix,
Braintrust) — none ship component attribution + counterfactual confirmation +
meta-evaluation.

**4 — Target users**
Platform / ML-ops engineers running agents in production; the on-call engineer
who gets "the triage agent failed" and needs the *decisive step*, not a 2,000-
line trace. A non-AI-specialist must be able to act on the output.

**5 — Why it needs AI (the gating requirement)**
Remove the model and Culprit ceases to exist. "Retrieval returned irrelevant
context" / "the summary asserts an unretrieved field" are semantic judgments
over unstructured traces — not keyword matching, not templates, not a wrapper.

**6 — Solution overview (architecture diagram)**
The courtroom: contracts = statute, judges = panel, evidence = cited trajectory
fields, verdict = report, confidence = jury agreement, counterfactual replay =
re-enactment, meta-evaluator = appeals court. Show `docs/images/architecture.png`.

**7 — How it works: the pipeline**
record → Shadow Monitor (online structural check) → multi-level LLM judges →
first-decisive-step attribution → **counterfactual replay** → verdict. Two
layers: deterministic invariants + semantic judges.

**8 — Engineering depth: the attribution algorithm**
Earliest high-confidence violation = decisive suspect; confirm by the *smallest
single-variable edit that flips the outcome to success* (Causal Responsibility
Score). Correlation → causation. *This is the 50% slide — linger here.*

**9 — Demo walkthrough** *(Prototype Quality)*
Live: `python -m culprit.run` on a real ticket — banner shows the **LLM judges**
firing. Then the dashboard: decisive node pulsing red, evidence, confidence,
validated repair. (Embed the ≤5-min video or screenshots.)

**10 — Explainability** *(15%)*
Every verdict: what the agent was supposed to do, what it did, where it diverged,
the cited evidence, the confidence, the recommended fix — for every run,
including passes. Low-confidence verdicts are surfaced for human review.

**11 — Evaluation: judging the judges** *(10%)*
Inject + fuzz labeled faults → attribution accuracy, per-category P/R/F1,
step-localization, counterfactual confirmation rate. Ground truth from
injection, not an LLM oracle. Show the meta-eval numbers.

**12 — Non-determinism, handled**
k-sample self-consistency (agreement = confidence); multi-agent debate on
genuine splits; invariant-over-actions checking so different *valid* paths don't
trip the monitor. Drift detected online (within-run) and batch (PSI/KL).

**13 — Honest limitations**
Counterfactual replay is the highest-risk component (degrades to correlation if
no edit flips). Headline meta-eval numbers come from the deterministic backend
on a small by-construction-labeled set — they prove the machinery, not wild-LLM
accuracy. Scoped to one JSM triage agent on purpose: general trace debugging
sits at ~11–14%; we trade breadth for measurable accuracy.

**14 — Scalability & next steps**
Async judge pool (judges are independent); gating keeps deep-path cost ∝ failure
rate; SQLite → Postgres, trajectories partitioned by day. Next: a stronger judge
model, real-enterprise validation, more agent types.

**15 — Close + ask**
Recap the one-liner + the defensible contribution (attribution → counterfactual
→ meta-eval). Repo + Docker + CI. Thank the judges; invite questions.

---

*Coverage check:* problem (2–3) · solution (6–8) · target users (4) · value prop
(3,5) · demo walkthrough (9) · limitations (13) · next steps (14). All §1.5.2
elements present in 15 slides.
