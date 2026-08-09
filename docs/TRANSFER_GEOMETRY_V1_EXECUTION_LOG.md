# Transfer Geometry Control V1 — execution log

This log freezes provenance for the single-agent OPE-GEOMETRY-V2 calibration.
It is not a society experiment and contains no router or adaptive agent state.

## Pre-execution snapshot

- UTC start: 2026-08-08 (recorded at implementation start)
- branch: `research/developmental-dynamics`
- start HEAD: `b8f8eb96cf8d1970876bbffd5d5580443fa39036`
- backend: DeepSeek Direct (`DeepSeekDirectBackend`), not OMP
- model: `deepseek-v4-flash`
- thinking: off
- existing test suite: 165 tests passing before this protocol
- real society calls in this protocol: 0
- frozen environment seeds: 8101, 8102, 8103, 8104, 8105
- geometries: GLOBAL, BLOCK, DIAGONAL

The existing OPE and CWDE qualification artifacts remain unchanged. The new
generator and manifests are versioned separately as OPE-GEOMETRY-V2.

## Frozen campaign completion

- GLOBAL: `3840/3840` logical, `3841` physical, one recovered `parse_error`, one
  semantic OOD, cost `US$0.087910732`.
- BLOCK: `3840/3840` logical, `3840` physical, one semantic OOD, cost
  `US$0.0817363904`.
- DIAGONAL: `3840/3840` logical, `3840` physical, one semantic OOD, cost
  `US$0.0711607456`.
- Total: `11520` logical, `11521` physical, `US$0.240807868`, final reserved
  amount `US$0.00`.
- All provider model metadata was `deepseek-v4-flash`; no duplicate terminal
  logical IDs were found.

Offline aggregation is materialized in
`reports/task-ecology/transfer-geometry-v1/`. Natural transfer is primary and
did not cleanly recover the preregistered geometry ordering; the detailed
boundary analysis is in `docs/EMPIRICAL_TRANSFER_OPERATOR_REPORT.md`.

## Execution rule

Offline generator/operator gates precede credential access. The only permitted
paid phase is the frozen 11,520-call single-agent calibration, with a US$1.50
campaign cap. No LLM society, Gate 2, or post-result redesign is permitted.
