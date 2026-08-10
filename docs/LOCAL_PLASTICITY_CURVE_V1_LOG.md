# Local Plasticity Curve V1 — Execution Log

## Pre-inference state

- protocol: `LOCAL-PLASTICITY-CURVE-V1`;
- starting HEAD and baseline test result recorded before freeze;
- model: DeepSeek Direct `deepseek-v4-flash`, thinking off;
- new hard cap: US$0.12;
- exact plan: 2,176 logical completions;
- geometry: DIAGONAL only;
- no society, routing, Gate 2, or cross-domain follow-up.

The cross-domain branch is closed as informative but nonessential. The current
experiment returns to the original minimal local-plasticity requirement.

## Freeze and execution

The manifest freezes exact V2 histories/probes, all prompt hashes, nested
horizons, exact Bayes opportunity, and deterministic interleaving before paid
inference. Execution and post-run analysis will append timestamps, physical
attempts, retries, OOD observations, cost, and final status here.

## Completed execution

- experimental commit: `829534f7a266b4a9d771ac1a207d83f759b46265`;
- manifest provenance commit: `ed9952d`;
- logical completions: 2,176/2,176;
- physical attempts: 2,176;
- technical retries: 0;
- semantic OOD: 0;
- model: `deepseek-v4-flash` for every event;
- fingerprint: `fp_a18b46594c_prod0820_fp8_kvcache_20260402`;
- observed cost: US$0.0555897104;
- status: `CLEAN`;
- finished: 2026-08-10T23:45:10Z.

## Offline result

The contemporaneous DIAGONAL curve passed L1–L6. `A0=.1250`,
`G_abs(8)=+.2734`, `G_rel(8)=+.2917`, and `I_abs/I_rel=.1211/.1172`.
No external inference was run after completion. A society remains design-only.
