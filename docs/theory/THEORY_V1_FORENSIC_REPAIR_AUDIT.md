# Theory V1 forensic repair audit

## Frozen specification

The governing mathematical documents are `THEORY_V1_FROZEN.md`,
`THEORY_V1_DERIVATION.md`, `THEORY_V1_PROSPECTIVE_PROTOCOL.md`,
`THEORY_V1_PREDICTION_REGISTRY.md`, and `THEORY_V1_FALSIFICATION_CRITERIA.md`
as sealed by the existing Theory V1 tags. They define `K^(k) -> T_k -> J`,
double-centered `Psi_spec`, niche-centered `R_spec`, the fixed macro grid, and
T1–T9 thresholds. No equation, threshold, seed, prompt, ecology, or raw
observation was changed by this repair.

## Executed data

- MICRO raw: `data/auto-research/theory-v1/micro_events.jsonl` (26,141 physical
  attempts; 26,112 logical terminals).
- Canonical restarted MACRO raw:
  `data/auto-research/theory-v1/macro/macro_events.jsonl` (186,393 physical
  completion attempts; 186,368 logical terminals).
- Canonical run ID: `theory-v1-macro-confirmatory-restarted-20260812`.
- Aborted serial run remains quarantined and is programmatically excluded.

Hashes, tag hashes, manifest hashes, and the exact 31-record checkpoint gap are
in `reports/theory-v1/repair/forensic_inventory.json`.

At the repair boundary the immutable raw hashes were MICRO
`a75193ceb1c788883bbe4f6941bfc64d3a182053f976a923dba08c4bfbade77f` and MACRO
`651661d36e533a1ec767bcb97ec7035112ad2c094f9d4cf2dd828424b7345ff6`; the
post-repair hashes are identical. The MICRO and MACRO manifest hashes are
`761972700ca981f59c1cfefa818662a3b16fe677419360e20dd4af8995c3c008` and
`792df8a7f3102ed58101f154bfb9e7b7c04b5fa53f73de32d9784c8761c75da6`.

## Prediction implementation discrepancies

The historical prediction manifest has 864 rows and 576 rows where the social
cell `k` differs from the `k_matrix` used to generate it. The frozen rule
requires the social cell's `k` to select `K^(k)`. A repaired population manifest
has exactly 36 rows (2 ecologies × 18 cells), with zero k/K mismatches.

The historical spectrum helper scored the full operator, allowing the uniform
niche mode to enter `R_spec`. The repaired evaluator constructs an orthonormal
basis for `1^perp` and scores `Q^T J Q`. The original sealed manifest is
preserved unchanged as historical implementation output.

## Scorecard implementation discrepancies

The old source exposed only partial T1–T9 helpers and no raw canonical
competence reconstruction. The forensic evaluator joins explicit keys
`(ecology,k,beta,epsilon,q)` and reconstructs bit/joint competence directly from
terminal raw checkpoint completions. It asserts exact denominators, unique
prediction keys, and no quarantined-run ingestion.

## Repair rules

1. Use pooled least-squares `K^(k)` across all eight MICRO seeds per ecology and
   capacity, because the frozen documents describe one population operator per
   ecology×k. Seed-mean and per-seed prediction interpretations are reported as
   sensitivity only.
2. Reconstruct missing auxiliary checkpoint rows only when an exact canonical
   raw completion exists; never impute.
3. Preserve all raw hashes and historical seals.
4. Treat the resulting scorecard as a forensic evaluation after MACRO, not as a
   prospectively sealed implementation.

## Status

This audit records implementation/analysis repair only. Scientific conclusions
are in `THEORY_V1_FORENSIC_ANALYSIS_REPAIR_REPORT.md` and closure is in
`THEORY_V1_CLOSURE.md`.
