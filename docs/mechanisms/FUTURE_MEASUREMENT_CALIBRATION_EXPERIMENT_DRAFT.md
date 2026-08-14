# Draft-only future measurement calibration (not authorized)

This document is a design note only. It is not a preregistration, does not
authorize paid calls, and does not define Theory V2.

## Motivation

The clean V1.1 endpoint has eight held-out probes per agent/niche/checkpoint.
The measurement-aware audit estimates marginal bit reliability near 0.60 in
V31 and 0.51 in AFFINE at that support, with joint reliability also limited.
The smallest useful next design would first improve the measurement channel,
then test whether a directional mechanism remains after cross-fitting.

## Candidate calibration

- Freeze the existing ecology, model, prompt, and social protocol.
- Increase untouched held-out probes only after a separate principal review;
  do not reuse the current probes as new data.
- Pre-register odd/even or another fixed split before outcomes.
- Use `A_bit` for specialization and `A_joint` for router calibration.
- Report seed-clustered split-half reliability, role-direction cosine, AB/BA
  disagreement, and null-calibrated cross-fitted reinforcement/innovation.
- Require a reliability target before interpreting churn, rather than choosing a
  target after seeing a result.

## Discriminating outcomes

1. Reliability rises and cross-fitted reinforcement is stable: persistent-role
   mechanisms become testable, but still require causal exposure variation.
2. Reliability rises and cross-fitted reinforcement remains weak/reversing:
   the prior churn interpretation is not a measurement artifact.
3. Reliability remains low: the correct conclusion is measurement
   non-identifiability, not a theory repair.

Any implementation, budget, seeds, or thresholds must be decided and sealed by
the principal researcher in a separate future task. No experiment was run here.
