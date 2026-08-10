# Cross-Domain Transfer Bottleneck V1 — Execution Log

## Pre-inference freeze

- Protocol: `CROSS-DOMAIN-TRANSFER-BOTTLENECK-V1`
- Purpose: localize the cross-domain transfer bottleneck after relation-only
  control failed.
- Model: DeepSeek Direct `deepseek-v4-flash`, thinking off.
- Seeds: 9201–9204; h=8; V2 probes and histories reused exactly.
- New logical calls: 2,944; hard external cap: US$0.15.
- Arms: LOCAL_REP, A0, A1, A2, A3, A4.
- No society, routing, teaching, new seeds, or follow-up inference.

The deterministic manifest freezes every prompt hash, source action,
identifiability value, correspondence identifier, representation mode, rule-table
metadata, answer-leak audit, and execution order before paid inference.

## Provenance

Starting HEAD, test count, forecast, execution HEAD, health, cost, and final HEAD
are recorded in the manifest and post-run report. Historical V2 and
Relation-Signal raw artifacts are not modified.

## Execution

- run command: `PYTHONPATH=src .venv/bin/python -m emergent_specialization.cross_domain_transfer_bottleneck --run --confirm-real`
- completed: 2026-08-10T22:25:50Z
- logical completions: 2,944/2,944
- physical attempts: 2,944
- technical retries: 0
- terminal semantic OOD: 1 (retained, not retried)
- observed cost: US$0.0653269344; hard cap US$0.15
- model identity: `deepseek-v4-flash` for all events
- status: `CLEAN`

## Offline analysis

The first analyzer pass found and fixed a non-scientific indexing bug: local
reference probes use the source-family prefix while cross probes use the
target-family prefix, despite sharing the same frozen latent probe suffix. The
corrected offline join was rerun; raw events and paid observations were not
changed. The derived report now includes per-seed and aggregate matrices,
geometry metrics, source-transport strata, anchoring diagnostics, and figures.

The ladder was partial: A1 improves over A0, A2 improves further, and explicit
rule tables (A3/A4) nearly solve the task. BLOCK cross-block and DIAGONAL
cross-domain qualification contrasts are structurally absent from the frozen
population, so those gates are reported as not identifiable rather than
imputed.

## Verification after completion

- no inference was launched after the completed campaign;
- no society, routing, teaching, new seed, or follow-up diagnostic was run;
- full test and compile results are recorded in the final research handoff;
- the raw append-only journal remains under
  `data/auto-research/cross-domain-transfer-bottleneck-v1/`.
