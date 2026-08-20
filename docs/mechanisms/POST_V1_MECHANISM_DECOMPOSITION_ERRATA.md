# Erratum: post-V1 mechanism decomposition

Status: supersedes the *interpretation* of selected derived mechanism terms;
does not modify raw observations, Theory V1/V1.1, or the previous report.

## Corrections

1. The earlier `A`/`mu` alignment was primarily an `A_bit` comparison, while
   the router posterior is updated by exact joint correctness. The corrected
   primary router construct is `A_joint`; `A_bit` remains the specialization
   construct used by `Psi_spec`.
2. Individual held-out probe rows are split deterministically by odd/even
   `probe_index`. Reliability and role-direction stability are therefore
   reported explicitly at the social-seed level.
3. The exact naive identity
   `Delta Psi = reinforcement + innovation` remains valid, but the terms are
   not unbiased latent mechanisms under noisy `Z_hat`. Same-measurement use
   introduces a negative self-noise term into reinforcement and positive noise
   into innovation.
4. Cross-half `Psi`, cross-time covariance, reinforcement, and innovation are
   now the measurement-aware diagnostics. Undefined or unstable cross-half
   cosines are retained as missing/unstable, not replaced by a favorable value.

## Interpretation change

The former statement that negative reinforcement plus positive innovation
*demonstrates differentiation churn* is withdrawn. The cross-fitted direction
is not reliable enough across the six clustered seeds per ecology to identify a
stable churn mechanism. The revised status is `H7 NON-IDENTIFIABLE`, with `H0`
measurement-limited dynamics moderate as a diagnostic. This is a correction of
inferential scope, not a rescue of Theory V1 or a new theory.

## What remains valid

Raw/state reconstruction, exposure-to-FIFO transmission, sharing-induced age
and overlap changes, the distinction between `A_bit` and `A_joint`, and the
need for held-out measurement halves remain valid. The original report and
tables are preserved as historical pre-correction artifacts.

## Reproducibility

The repair is registered in
`reports/post-v1-measurement-aware/analysis_registry.json`, uses no external
calls, and preserves all five canonical raw SHA-256 hashes. The canonical
measurement-aware report is
`docs/mechanisms/POST_V1_MEASUREMENT_AWARE_MECHANISM_REPORT.md`.
