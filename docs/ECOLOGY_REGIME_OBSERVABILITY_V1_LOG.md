# Ecology Regime Observability V1 — execution log

## Scope

Offline-only audit of the V2 Bayes comparison. No external model, society,
routing, credential, or network call is permitted.

- starting HEAD: `489c9677316a28891d65494ed543c47d33fb4337`
- branch: `research/developmental-dynamics`
- audit date: 2026-08-10
- external inference budget: **US$0.00**
- V2 raw data and manifest: preserved unchanged

The baseline suite was run before analysis. The audit implementation itself is
analysis-only and imports no provider or credential module. Final test and
compile counts are recorded in the handoff report.

## Frozen source of truth

The V2 `exact_bayes` function receives the realized `geometry`, source family,
target family, history, and target probe. `render_user` serializes semantic
cases and resolved labels; `SYSTEM_PROMPT` and `OUTPUT_INSTRUCTION` do not
mention `GLOBAL`, `BLOCK`, `DIAGONAL`, or a sharing relation. Thus V2's old
`L*_obs` was conditioned on a simulator variable unavailable to the model-facing
learner for cross-domain comparisons.

This audit does not rewrite V2. It adds the missing random variable `G` and
recomputes hidden, relation-aware, and full-regime normative references offline.
