# Post-V1 measurement-aware mechanism repair

## Executive answer

The previous negative-reinforcement/positive-churn decomposition was algebraically
correct for the measured matrices but is not automatically a latent dynamical
decomposition. This repair separates `A_bit` (specialization) from `A_joint`
(the router's actual feedback target) and uses independent odd/even held-out
probe halves. The cross-fitted results and reliability ceilings are now the
primary mechanism evidence; the prior report remains preserved as a pre-
measurement-error analysis.

**Theory V1.1 remains prospectively NOT SUPPORTED.** This reanalysis does not
rescue it, revise it, or define Theory V2.

## Data integrity and provenance

Only clean V1.1 Stage A, MICRO, and canonical MACRO raws were used. External
calls: **0**; new cost: **US$0.00**. Raw hashes before/after are identical.
The canonical MACRO has 62,976 terminal logical observations from 62,995
physical attempts. Historical harness-confounded V1 and the quarantined serial
run were excluded. The registered plan and exact hashes are in
`reports/post-v1-measurement-aware/analysis_registry.json`.

## Measurement model and bias

With `Z_hat_t = Z_t + epsilon_t`, same-half naive reinforcement contains
`-2||epsilon_t||²` in expectation, while naive turnover contains positive
variance terms from both checkpoints. Thus an exact observed identity can have
biased components. Cross-fitting estimates latent cross-products using
independent probe halves and does not clip negative finite-sample values.

## Reliability and role geometry

The primary split is odd probe IDs versus even probe IDs. Reliability is reported
by ecology, seed, cell, checkpoint, and construct. Bit role-direction reliability
is measured by `cos(Z_bit^a,Z_bit^b)` and specialist identity agreement; joint
reliability is reported separately because it is the router construct.

At representative private adaptive C3/t=128, mean split-half Pearson values
are about 0.44 (V31 bit), 0.29 (AFFINE bit), 0.21 (V31 joint), and -0.08
(AFFINE joint); corresponding role-geometry cosines are about 0.49, 0.37,
0.28, and 0.06. Specialist-agreement means are 0.33, 0.42, 0.50, and 0.25.
These are six-seed summaries, not response-level replications. The adequacy
curve estimates eight-probe bit reliability near 0.60 (V31) and 0.51 (AFFINE),
with 16 probes near 0.75 and 0.68; these are extrapolations, not imputations.

## Naive versus cross-fitted dynamics

The exact naive decomposition is reproduced for validation. The cross-fitted
quantities are `Psi_cross`, cross-time covariance, `reinforcement_cf`, and
`innovation_cf`, with AB/BA disagreement exposed. The result must be read with
the reported reliability and six-seed uncertainty. The revised classification
does **not** retain “differentiation churn” as a robust mechanism; H7 is
measurement-limited/non-identifiable unless cross-fitted direction remains
stable.

At t=128, V31 C3 mean reinforcement changes from about -0.0141 (naive) to
-0.0040 (cross-fitted), and AFFINE C3 from -0.0070 to +0.0038. Mean innovation
changes from about 0.0137 to 0.0041 (V31) and 0.0084 to 0.0004 (AFFINE).
The fixed-latent 1,600-replicate offline null produces naive reinforcement
about -0.0235 and naive innovation +0.0234, while cross-fitted values are
approximately +0.0003 and -0.0003. This shows that the prior sign pattern can
arise without latent role change. Undefined/unstable cross-fitted cosines are
kept missing, with raw ratios and AB/BA disagreement in the CSV.

## Router construct alignment

`mu` is calibrated primarily against `A_joint`, not `A_bit`. The report separates
calibration, ranking, and specialization relevance, and supplies joint-belief
regret plus secondary `mu`–`A_bit` association. OOF B0/rolling/EWMA diagnostics
use held-out social seeds. No router policy was changed.

At t=128, `mu`–`A_joint` centered cosine averages about 0.16 (V31) and 0.05
(AFFINE), with top-agent agreement about 0.33 and 0.24. OOF B0/rolling/EWMA
joint-belief R² is negative in both ecologies. The separate calibration-curve
and `A_joint`–`A_bit` relationship tables do not impose `A_joint=A_bit^3` or
bit-independence. Calibration, ranking, and specialization relevance are
reported as distinct questions.

## Exposure, memory, and plasticity

The C0 random-private analysis predicts future held-out `A_bit` from independent
baseline halves plus own/foreign exposure. This is the measurement-aware
cross-half/ANCOVA diagnostic, clustered by social seed, not an unrestricted
causal claim. M0–M4 remain a fixed ladder; no new memory representation was
searched.

## MICRO and sharing

K half-A/half-B stability and finite-probe double-swap sensitivity are reported
without fitting nonlinear alternatives. Sharing timescale is decomposed into
the mechanically expected update rate `u(q)` (`.25`, `.625`, `1.0` for q=`0`,
`.5`, `1`) and observed FIFO age/span/overlap. This prevents treating mechanical
turnover as an independently identified social mechanism.

K half-A/B tables include matrix correlation, cosine, max-entry difference, and
real-eigenvalue stability. Double-swap R² is compared with deterministic
Bernoulli measurement nulls; no nonlinear alternative is fitted. Sharing
endpoint age/span/overlap (V31 q=0/.5/1: approximately 17.9/30.8/0,
5.9/11.0/0.376, 3.5/7.0/1.0) follows the expected horizons 32, 12.8, and 8.

## Revised mechanism evidence

H0 measurement-limited dynamics is a meta-diagnostic. H1 router staleness, H2
selection-on-noise, H3 exposure-memory attenuation, H4 memory-state insufficiency,
and H5 MICRO-to-MACRO extrapolation remain inconclusive. H6 sharing-timescale
remains moderate but is largely mechanically implied. H7 differentiation churn
is non-identifiable after the measurement correction. H8 is weakened to a weak
descriptive synthesis. Full evidence, caveats, and previous classifications are
in `revised_mechanism_evidence.json` and the CSV tables.

## What survives and what is withdrawn

Surviving claims are limited to: raw/state reconstruction is valid; `A_bit` and
`A_joint` are distinct constructs; probe reliability is a real ceiling; sharing
changes FIFO timescale/overlap; and cross-fitted diagnostics are required before
calling a directional mechanism. The strong pre-correction statement that
negative reinforcement demonstrates differentiation churn is withdrawn. The
previous report is not rewritten.

## Theory readiness and next step

Current measurements are not adequate for a trustworthy dynamical Theory V2.
The project should choose between a measurement-calibration-first design or an
empirical feedback-closure paper; no new experiment is authorized here. A draft
measurement calibration protocol is included only if the adequacy curve and
role reliability justify it. **NEXT ACTION: PRINCIPAL RESEARCHER REVIEW.**

## Outputs

- state/probe-half reliability tables;
- cross-fitted Delta-Psi dynamics and AB/BA sensitivity;
- measurement-noise null simulation;
- construct-aligned router calibration and regret;
- cross-half C0 plasticity;
- MICRO K stability and sharing-timescale arithmetic;
- `A_joint` versus `A_bit` relationship and fixed-bin router calibration curves;
- naive/cross-half/noise-subtracted `Psi_spec` summaries;
- measurement adequacy, revised evidence, figures, errata, and updated theory requirements.

Summary JSON: `reports/post-v1-measurement-aware/summary.json`.
