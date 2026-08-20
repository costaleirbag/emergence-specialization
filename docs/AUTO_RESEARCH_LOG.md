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

## 2026-08-08 — AR-001 implementation and safety amendment

- The task-ecology review does not make the explicit-rule control redundant.
  Offline algebra can prove that a context identifies a rule, but cannot decide
  whether the frozen model executes that rule reliably. AR-001 therefore still
  distinguishes live H7 (execution) from H4 (induction/prompting) more directly
  than another offline ecology analysis. It does **not** validate GF(7) as a
  broad functional ecology.
- Frozen config SHA256:
  `462aa3a7ccbdac52be1d34050eb9c497ee0da9a9eab03740996e0080b23e6d90`.
- Runner implementation commit: `468a6f2` (`Add fail-closed explicit rule
  diagnostic`). Frozen module SHA256:
  `b10f649b902f7f1a93fa9b576740f4a9c0465ed7059cabe0b9495421d6f369d8`.
- Frozen balanced probe commit: `13f40d9`; probe SHA256 remains
  `7c5370122b553dafbd1ef950f3b4de9ca9636f7c3922cb31800169638b59c2df`.
- Retry policy is the original preregistered technical set only: transport,
  empty response, or parse/schema failure, at most one retry. Rate limits and
  provider/server errors are not newly authorized categories.
- Cost controls reserve US$0.005 before each attempt. The frozen price/token
  bound is US$0.00462336 per attempt; unknown cost retains the entire
  reservation. The experiment hard observed cap is US$0.05 and the initialized
  session ledger has US$2.00 available, with experiment-scoped spent/reserved
  reconciliation.
- Resume freezes config, probe, prompts/logical IDs, implementation hash, Git
  HEAD, and relevant worktree state; terminal failures cannot resume without an
  explicit amendment. Output execution is single-process locked.
- Offline validation at this amendment: **162 tests passed**, compileall PASS,
  preflight reports 168 logical calls, 336 physical ceiling, balanced labels,
  no credential access, and no network access.
- Three implementation reviews were required. The first two independently
  blocked unsafe versions; no paid call occurred. Final execution eligibility
  remains contingent on one last adversarial review of the committed state.

## 2026-08-08 — AR-001 final execution decision

- Independent adversarial verdict on committed HEAD `2424764`: **GO**, with no
  remaining execution blocker. Fourteen focused tests, the 162-test full suite,
  compileall, ledger state, clean scientific provenance, and preflight passed.
- Explicit budget question: **yes**, AR-001 distinguishes the live execution
  bottleneck from induction/prompting in a way that offline ecology analysis
  cannot. Its value is diagnostic and does not authorize a semantic ecology or
  a new society run.
- Authorized action is exactly one resumable AR-001 run under the frozen 168-
  logical-call protocol, US$0.05 experiment cap, and US$2 session ledger. No
  adaptive extension is authorized.
- Residual conservative behavior: a paid transport failure without usage holds
  its US$0.005 reservation and makes the run terminal rather than risking an
  unaccounted retry.

## 2026-08-08 — AR-001 zero-call credential boundary incident

- The first launch attempt failed while reading macOS Keychain from the
  filesystem-sandboxed process. It ended before backend construction and before
  any physical request: **0 model calls, US$0.00 cost, 0 ledger reservation**.
- A status-only check outside that sandbox returned `status=configured` using
  the expected macOS Keyring backend; no credential value was printed or
  persisted.
- The terminal manifest was preserved at
  `data/auto-research/explicit-rule-execution-v1-precall-failure-20260808T140745Z/`.
  It was not treated as a resumable scientific run. Because no request occurred,
  one fresh launch in the original frozen output path is authorized outside the
  sandbox. This is an infrastructure-boundary correction, not a scientific
  retry, protocol change, or added call.

## 2026-08-08T14:12:07Z — AR-001 completed and audited

- Health: **COMPLETE/CLEAN**. 168/168 unique logical responses, 168 physical
  attempts, 0 retries, 0 errors, 0 semantic OOD responses, one requested/returned
  model (`deepseek-v4-flash`) and one provider fingerprint.
- Primary result: 153/168 correct = **0.910714**, above the preregistered 0.85
  execution-reliability threshold. World accuracies: ALPHA 39/42, BETA 41/42,
  GAMMA 37/42, DELTA 36/42.
- Reliability: 44/56 exact prompts had three-way answer agreement; mean pairwise
  answer agreement was 0.845. Confidence was 1.0 for every response, including
  all 15 errors, so it provided no discrimination in this control.
- Usage/cost: 18,060 input + 2,030 output = 20,090 tokens with 100% usage
  coverage; configured-price cost US$0.0030968. Ledger and manifest reconcile;
  no reservation remains.
- **Post-run design limitation:** direct raw/probe audit found `x=0` for all 56
  tasks (`y=0..13`). The frozen probe constructor selected the first two items
  per answer label in lexicographic order. Consequently AR-001 tests explicit
  modular execution only on `z=b*y+c`; it cannot establish execution of `a*x`
  or general bivariate affine rules. The result is not discarded, but H7 is
  only weakened/partially refuted.
- Independent raw validation reproduced counts, accuracy, agreement, usage,
  cost, latency, provider identity, and ledger reconciliation without reading
  `report.json` as authority.

## 2026-08-13 — post-V1 mechanism decomposition (offline, zero calls)

- Registered the mechanism plan and analysis registry before inspecting derived
  mechanism results (`c74294f`). Primary inputs were only the clean Theory V1.1
  Stage A, MICRO, and canonical MACRO raws; historical harness-confounded V1
  data were excluded from primary inference.
- Reconstructed a complete state panel for 2 ecologies × 6 social seeds × 8
  cells, including t=0 and t=1..128 router posterior, expected routing,
  routing/sharing draws, online correctness, FIFO memory cases with timestamps
  and provenance, and held-out checkpoint competence. Raw event hashes were
  identical before and after analysis.
- Computed the chain `A -> mu -> p -> E -> M -> A'`, reliability, OOF belief and
  memory-model diagnostics, exposure/memory timescale, MICRO-to-MACRO transport,
  and the exact double-centered Delta-Psi reinforcement/innovation identity.
- Descriptive result: exposure and memory transmit, but competence movement is
  often anti-aligned with the current centered role direction; sharing changes
  FIFO age and overlap; router staleness, memory representation, and local-K
  transport remain inconclusive under low reliability and six clustered seeds.
  H6 sharing-timescale and H8 multiple-bottleneck synthesis are moderate
  descriptive evidence; no causal mechanism or Theory V2 was defined.
- Outputs are under `reports/post-v1-mechanisms/`; final validation and report
  generation remain part of this offline closure. External calls: **0**; cost:
  **US$0.00**.

## 2026-08-13 — post-V1 measurement-aware mechanism repair (offline, zero calls)

- Registered a separate measurement-aware analysis before computation. The
  canonical raw SHA-256 values were unchanged before/after; historical and
  quarantined V1 data remained excluded.
- Reconstructed individual held-out probes and fixed odd/even split halves.
  `A_bit` is primary for specialization/Psi; `A_joint` is primary for router
  calibration because `mu` updates on exact joint correctness.
- Cross-fitted Delta-Psi terms, AB/BA stability, construct-aligned router OOF
  diagnostics, C0 cross-half exposure, fixed M0–M4 ladder, MICRO half
  stability, sharing timescale, adequacy curves, and deterministic measurement
  nulls were generated under `reports/post-v1-measurement-aware/`.
- The old churn interpretation is downgraded: H7 is **NON-IDENTIFIABLE**;
  H0 measurement-limited dynamics is a moderate diagnostic; H6 sharing
  timescale remains moderate but mechanically implied. Theory V1/V1.1 remain
  closed; Theory V2 is undefined. External calls: **0**; cost: **US$0.00**.
