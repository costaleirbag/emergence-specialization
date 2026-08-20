# Observable Learner Calibration V1 — Execution Log

This file records the frozen calibration gate without exposing credentials.

## Pre-inference record

- Protocol: `OBSERVABLE-ECOLOGY-LEARNER-CALIBRATION-V1`
- Starting scientific HEAD: `9cf00acaa8b4a4700a8ebef3813e5d1fdd060358`
- V3.1 scientific commit: `9cf00ac`
- Provider/model: DeepSeek Direct / `deepseek-v4-flash`
- Thinking: off
- Hard new external budget: US$0.20 (including technical retries)
- Seeds: `9201, 9202, 9203, 9204`
- Geometries: GLOBAL, BLOCK, DIAGONAL
- Natural history: h=8; held-out probes: 6 per target cell
- Expected logical calls: 1,440 (288 baseline + 1,152 transfer)

## Local audit

V3.1 artifacts were checked locally, rather than accepted solely from the prior
terminal report. `gate_summary.json` reports O1–O10 all PASS; observation loss
MAE/MAX for J and L* is zero; renderer collision and theta-leakage counts are
zero; family recovery is 100%; and the latent prior is marked unchanged. The
V3/V3.1 unit tests and the calibration manifest tests pass before any credential
access.

## Execution policy

The manifest is immutable after commit. `events.jsonl` is append-only and each
logical context has a stable hash. Resume skips terminal logical IDs and never
reruns a scientific observation. Invalid decision-domain output is scientific
out-of-domain data, not a retry. Only technical/transport/parse failures may
consume the bounded second attempt.

## Post-inference append-only fields

After execution, append the final run status, physical attempts, retries by
category, semantic OOD count, provider model/fingerprint, usage coverage,
latency, observed cost, analysis paths, and package SHA-256. No society result is
to be inferred from this gate.

## Final execution record (2026-08-09)

- Status: completed CLEAN; logical coverage 1,440/1,440.
- Physical attempts: 1,440; technical retries: 0; semantic OOD: 0.
- Model: `deepseek-v4-flash`; one recorded provider fingerprint.
- Observed cost: US$0.0268121448; mean/median latency: 1.0829/1.0566 s.
- Learner qualification: **PARTIAL**. A–H results and raw-derived matrices are
  in `docs/OBSERVABLE_LEARNER_CALIBRATION_V1_REPORT.md` and
  `reports/task-ecology/observable-learner-calibration-v1/`.
- Package: `.artifacts/packages/observable-learner-calibration-v1-package.tar.gz` (SHA-256 is stored
  in the adjacent `.sha256` file).
- External inference is stopped. No society, Gate 2, tuning, model switch, or
  follow-up paid call was executed.
