# Autonomous research log

This notebook is chronological and append-only at the level of dated entries.
Later corrections must identify the earlier statement they amend; raw artifacts
are never rewritten to make a prediction look prespecified.

## 2026-08-08T13:28:01Z — session start and provenance freeze

- Research mode: adaptive mechanism investigation.
- Scientific objective: reduce uncertainty about the developmental dynamics of
  initially exchangeable LLM societies; producing specialization is not an
  optimization target.
- Starting branch: `research/developmental-dynamics`.
- Starting HEAD: `3db7f54ec93254a570dd1f2e3b43870fdcee1dad`.
- Codex CLI: `codex-cli 0.147.0`.
- Parent model: GPT-5.6 Sol is the requested/session PI role; the exact serving
  model identity is not exposed programmatically by the local CLI.
- Configured worker profiles: `luna_explorer`, `luna_analyst`,
  `luna_implementer`, and `luna_reviewer` under `.codex/agents/`.
- Configured worker model: `gpt-5.6-luna`; reasoning effort is `medium` for
  explorer/analyst/implementer and `high` for reviewer.
- Subagent routing diagnostic: two harmless spawns through the configured Luna
  profiles failed before starting with `Unknown model gpt-5.6-luna`; the runtime
  advertised only `gpt-5.6-sol` and `gpt-5.6-terra`.
- `SUBAGENT MODEL ROUTING: UNVERIFIED / UNAVAILABLE IN THIS RUNTIME`.
- Bounded fallback workers were therefore launched explicitly with
  `gpt-5.6-terra`; no claim of Luna context or cost savings is made.
- External DeepSeek Direct inference budget for this session: **US$2.00**.
- OMP and Bitwarden are prohibited for this session.
- Starting working tree contained user-owned/untracked files and existing raw
  artifacts. They are preserved; no destructive cleanup is authorized.

### Existing experiment/raw-data inventory at session start

- `developmental-dynamics-v2`: clean response-semantics 2×2, 40 complete runs,
  22,400 logical completions, stored under
  `data/runs/campaigns/developmental-dynamics-v2/` and indexed by its campaign
  manifest.
- `memory-learnability-v1`: complete single-agent calibration, 9,600 logical
  queries and 9,669 physical attempts; raw append-only JSONL is about 26 MiB.
- `memory-representation-thinking-v1`: full thinking-off arm and incomplete
  thinking-on arm, 18,031 recorded physical attempts; raw append-only JSONL is
  about 47 MiB.
- Historical exploratory/private/shared and v1 campaign artifacts remain
  present but must not be pooled with clean v2.
- Manifest-authoritative fixed society probe hash:
  `cb234422389ff7d5a04566112a483f147e4a3d1212b1c69fbb0396ec9ca4c55e`.
- Balanced representation/thinking probe hash:
  `7c5370122b553dafbd1ef950f3b4de9ca9636f7c3922cb31800169638b59c2df`.

### Baseline health before experiment-critical changes

- `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v`:
  **132 passed, 0 failed, 0 skipped**.
- `PYTHONPATH=src .venv/bin/python -m compileall -q src`: **PASS**.
- Real model calls made by this session so far: **0**.

### Initial research ordering

Free, high-information work comes first: exact GF(7) identifiability and a
symbolic positive control; raw-data/provenance audit; prompt mechanism audit;
existing-data anchoring tests; theory and HSE robustness. A paid experiment is
eligible only after a frozen preregistration, implementation review, passing
tests, and a cost-ledger check.

## 2026-08-08T13:40:02Z — EXPERIMENT AR-001 preregistration

- **Experiment ID:** `AR-001-explicit-rule-execution-v1`.
- **Discovery/confirmation label:** microscopic diagnostic positive control;
  neither society evidence nor confirmation of the anchoring hypothesis.
- **Hypotheses addressed:** H7 (execution bottleneck), with implications for H4
  (induction bottleneck).
- **Exact question:** when the correct affine rule is explicitly supplied, can
  thinking-off `deepseek-v4-flash` reliably execute it on balanced unseen
  inputs modulo seven?
- **Why this is higher-value now:** exact GF(7) auditing has already shown that
  the generator and almost all `k=4/8` contexts are mathematically learnable.
  Before paying for coefficient induction or memory-order manipulation, the
  arithmetic-execution link must be isolated. This design is smaller and less
  confounded than either alternative.
- **Protocol:** single stateless DeepSeek Direct completion; no society, router,
  agent identity, memory, or adaptive feedback. Reuse the frozen 56-task
  balanced probe manifest (14 per world, exactly two per correct label 0--6;
  hash `7c5370122b553dafbd1ef950f3b4de9ca9636f7c3922cb31800169638b59c2df`).
  For each task, explicitly state the correct world coefficient triple and the
  formula `z=(a*x+b*y+c) mod 7`, then request the normal answer/confidence JSON.
  Use four worlds, all 56 probes, three independent calls per exact prompt,
  thinking disabled, `max_tokens=128`, and no provider sampling seed (not
  exposed). Probe order is deterministic and results are append-only.
- **Primary outcome:** valid-response accuracy overall and by world. This is a
  gross capability diagnostic; task/world and exact-prompt replicate are
  reported, not treated as 168 independent scientific societies.
- **Secondary outcomes:** exact three-way/pairwise answer and correctness
  agreement, confidence/correctness relationship, semantic OOD responses,
  technical errors/retries, latency, token usage, provider model/fingerprint,
  and observed cost.
- **Expected patterns:** accuracy >=0.85 supports reliable execution and shifts
  the main bottleneck toward induction/prompting; accuracy <=0.35 supports an
  execution bottleneck under this exact protocol; an intermediate result is
  ambiguous. These thresholds were chosen before data inspection and are not
  publication-level tests.
- **Technical retry semantics:** transport, empty content, or malformed schema
  may be retried once. A valid wrong or out-of-domain integer is scientific data
  and must never be retried.
- **Stopping rule:** stop after 168 successful logical responses or when a hard
  cost/attempt guard fires. Do not increase sample size adaptively based on
  accuracy.
- **Logical call count:** 56 probes x 3 replicates = **168**.
- **Maximum physical attempts:** **336**.
- **Projected cost:** approximately US$0.01 from recent thinking-off calls;
  conservative experiment hard cap **US$0.05**.
- **Global cost check before implementation:** cumulative autonomous-session
  cost US$0.00; worst-case experiment cap leaves US$1.95 of the US$2.00 global
  budget.
- **Implementation base:** `e3577ce5a2ca19b5ffce930d5c41ef36d7619ba4`.
- **Implementation commit/hash:** pending implementation and adversarial review;
  it must be recorded in a dated amendment before any paid call.

## 2026-08-08 — task-ecology priority steer and AR-001 pause

- New high-level concern: the four GF(7) worlds vary coefficients inside one
  cognitive operation and may be a poor sole substrate for broad functional
  specialization.
- Added H13, task-ecology transfer geometry, and formalized the directed causal
  learning-transfer matrix `L_cd(h)` in
  `docs/TASK_ECOLOGY_TRANSFER_GEOMETRY.md`.
- Existing data already suggest the first GF(7) failure regime: on truly
  non-alias thinking-off probes, targeted experience does not produce a clear
  positive same-world gain. This is descriptive because the old protocol was
  not designed as a full randomized transfer matrix.
- GF(7) is retained as an exact mechanistic/null ecology. It is not discarded,
  and its narrow parameter-specialization interpretation remains testable.
- The literature indicates that task relations should be measured through
  directed transfer and that recent work already claims spontaneous LLM niche
  specialists on heterogeneous streams. The prospective novelty is therefore
  ecology-to-organization prediction, not merely “roles emerge”.
- `AR-001-explicit-rule-execution-v1` remains scientifically useful for
  separating arithmetic execution from induction, but paid execution is paused
  while this construct-validity analysis is completed.
- An adversarial implementation review independently blocked the initial AR-001
  runner because token-derived cost guards, global ledger updates, credential
  configuration, resume identity, provider-model validation, and health states
  were unsafe. No real call occurred. Remediation is offline-only and must pass
  a second review before the experiment can become eligible again.
- Worker economy changed immediately to at most two concurrent bounded workers.

