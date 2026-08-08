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

