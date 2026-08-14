# Post-V1 measurement-aware mechanism repair

## Executive result

This was a deterministic, zero-call reanalysis of the consumed clean Theory
V1.1 Stage A, MICRO, and canonical MACRO observations. It did not change the
Theory V1/V1.1 verdict and did not define Theory V2. The previous
negative-reinforcement/positive-innovation decomposition is algebraically
correct for the observed matrices, but its latent-mechanism interpretation is
not secure: same-measurement noise mechanically pushes naive reinforcement
down and innovation up. Cross-fitting removes that dominant self-noise term,
but the remaining direction is still seed- and construct-limited rather than a
cleanly identified churn mechanism.

The strongest defensible update is therefore **measurement-limited dynamics,
not demonstrated differentiation churn**. Router calibration is evaluated
against `A_joint`, the construct that actually updates `mu`; `A_bit` remains
the specialization/Psi construct. The router–joint relationship is weak and
out-of-fold state prediction is below a useful held-out baseline. Sharing does
produce the mechanically expected FIFO timescale/overlap changes, but this
does not identify a competence consequence.

## Scope, provenance, and raw integrity

Only the clean V1.1 Stage A, MICRO, and canonical restarted MACRO raw logs were
used. Historical harness-confounded V1 data and the quarantined serial MACRO
run were excluded. No API credential was read and no external model call was
made (`US$0.00`). The canonical MACRO contains 62,976 terminal logical
observations from 62,995 physical attempts, with the previously recorded
technical retries and provider fingerprint. SHA-256 hashes before and after
the analysis are identical; see `raw_hash_manifest.json`.

The prior `POST_V1_MECHANISM_DECOMPOSITION_REPORT.md` and its tables remain
unchanged and are explicitly pre-measurement-error artifacts. This report and
all new tables are separate under `reports/post-v1-measurement-aware/`.

## Measurement model and estimands

For specialization, the primary observable is
`A_bit[i,c,t]`, the mean correctness of the three binary decisions. Its
double-centered matrix is the input to `Psi_spec`. For router calibration, the
primary observable is `A_joint[i,c,t]`, the exact three-bit correctness rate,
because the Beta-Bernoulli router updates on exact joint correctness. `mu` vs
`A_bit` is retained only as a secondary cross-construct diagnostic.

Held-out probe rows were reconstructed from the canonical checkpoint events.
The fixed, outcome-independent split is odd `probe_index` versus even
`probe_index`; each half contains four probes per agent/niche. Social seeds,
not agent×niche×probe rows, are the uncertainty unit.

For `Z_hat(t)=Z(t)+epsilon(t)`, the same noisy estimate is used in both the
baseline and difference of the naive statistic:

`2 <Z_hat_t, Z_hat_t' - Z_hat_t>`.

With zero-mean independent errors, its expectation contains
`-2 E||epsilon_t||²`; the squared increment contains positive error variance
from both checkpoints. Thus the exact identity
`Delta Psi = reinforcement_naive + innovation_naive` does not make those two
terms unbiased latent mechanisms.

The cross-fitted quantities use independent halves:

`C_t = <Z_t^a,Z_t^b>`;

`C_tt' = 0.5(<Z_t^a,Z_t'^b> + <Z_t^b,Z_t'^a>)`;

`reinforcement_CF = 2(C_tt' - C_t)/(N K)`;

`innovation_CF = (C_t' + C_t - 2 C_tt')/(N K)`.

No negative value was clipped. AB/BA differences and undefined near-zero
cross-half cosines are reported rather than hidden.

## Split-half reliability and role geometry

At the representative adaptive private cell C3 and endpoint t=128, mean
split-half Pearson reliability is approximately 0.44 (V31 bit), 0.29
(AFFINE bit), 0.21 (V31 joint), and -0.08 (AFFINE joint). Mean role-geometry
cosines are approximately 0.49, 0.37, 0.28, and 0.06 respectively, with
specialist-agreement means of 0.33, 0.42, 0.50, and 0.25. These are finite
six-seed summaries, not independent response-level evidence. The full table
contains every ecology, seed, cell, checkpoint, and construct.

The measurement-adequacy extrapolation indicates that eight total probes are
only a marginal reliability regime: estimated bit reliability is about 0.60
(V31) and 0.51 (AFFINE), while 16 probes would be about 0.75 and 0.68. This
curve is a design diagnostic, not an imputed correction or an authorization for
new inference.

## Naive versus cross-fitted dynamics

At endpoint t=128, the naive reinforcement remains negative across most cells,
while cross-fitted reinforcement moves toward zero and can become positive in
some high-beta/shared cells. For example, in V31 C3 the mean naive and
cross-fitted reinforcement are about -0.0141 and -0.0040; in AFFINE C3 they
are about -0.0070 and +0.0038. Cross-fitted innovation is also smaller than
naive innovation (V31 C3 about 0.0041 versus 0.0137; AFFINE C3 about 0.0004
versus 0.0084). The interval identity holds to floating-point precision.

Cross-fitted role cosines are left undefined when cross-half energy is
non-positive, near zero, or produces a non-cosine ratio; raw values and
AB/BA disagreement remain in the CSV. This is a substantive stability warning,
not a plotting omission. The deterministic 1,600-replicate fixed-latent
measurement null gives naive reinforcement about -0.0235 and naive innovation
about +0.0234, while cross-fitted means are approximately +0.0003 and -0.0003.
The null is methodological only, not society data; it demonstrates why the
previous sign pattern cannot by itself establish churn.

## Router construct alignment and staleness

At t=128, `mu` versus `A_joint` has mean centered cosine about 0.16 (V31) and
0.05 (AFFINE), with top-agent agreement about 0.33 and 0.24. The secondary
`mu` versus `A_bit` alignment is not substituted for this construct-correct
result. Held-out joint-belief models (B0 cumulative, rolling, and EWMA) have
negative mean OOF R² in both ecologies; the best simple models remain below a
useful predictive baseline. This supports a measurement-limited/inconclusive
router-staleness classification, not a causal claim that the router is wrong.

## Exposure, memory, and sharing timescale

The fixed C0 random-private cross-half ANCOVA shows a positive own-exposure
coefficient in V31 at early endpoints (about 0.070 at t=16, declining toward
0.034 at t=128 in one direction) and smaller/less stable effects in AFFINE.
Foreign-exposure coefficients are near zero or negative. These are descriptive
seed-clustered associations, not an intervention or a causal exposure effect.

Sharing changes the memory timescale as mechanically predicted by
`u(q)=q+(1-q)/N`: at q=0, q=.5, and q=1 the expected horizons are 32, 12.8,
and 8 global tasks. In V31 the observed endpoint mean age/span are about
17.9/30.8, 5.9/11.0, and 3.5/7.0; exact-case overlap is 0, 0.376, and 1.0.
AFFINE is similar (18.2/30.5, 6.4/11.4, and 3.5/7.0; overlap 0, 0.370, and
1.0). The competence implication is not isolated.

## MICRO and memory representation diagnostics

The fixed M0–M4 ladder is recomputed with held-out social seeds. No added
features or nonlinear theory were fit. The MICRO half-split K and double-swap
tables expose substantial finite-probe variability; observed half-split R² is
often negative and the Bernoulli measurement null has similarly broad/negative
R². This limits transport claims from microscopic K to macro states, but does
not make K meaningless or justify changing Theory V1.

M4 is explicitly labeled as a prior full-target diagnostic copied for
sensitivity context; it is not relabeled as a newly cross-fitted fit. Primary
M0–M3 cross-half results remain separate.

## Revised mechanism evidence

| hypothesis | revised status | reason |
|---|---|---|
| H0 measurement-limited dynamics | MODERATE diagnostic | low/variable reliability and null-calibrated naive bias |
| H1 router staleness | INCONCLUSIVE | construct-correct `A_joint` OOF calibration is weak, but noisy |
| H2 selection on noise | INCONCLUSIVE | no adaptive intervention |
| H3 exposure-memory attenuation | INCONCLUSIVE | cross-half association only |
| H4 memory-state insufficiency | INCONCLUSIVE | fixed M0–M3 ladder does not identify a winner |
| H5 MICRO–MACRO extrapolation | INCONCLUSIVE | K half stability/coverage remain limited |
| H6 sharing timescale | MODERATE, mechanical | age/span/overlap follow update-rate arithmetic |
| H7 differentiation churn | NON-IDENTIFIABLE | cross-fitted direction is reliability-limited |
| H8 multiple bottlenecks | WEAK synthesis | no causal closure decomposition |

The old strong claim “negative reinforcement demonstrates differentiation
churn” is withdrawn. What survives is narrower: exposure asymmetry reaches FIFO
memory; sharing changes temporal coverage; `A_bit` and `A_joint` are distinct
constructs; and directional mechanism claims require independent measurement
halves.

## What this does not establish

- It does not establish a new dynamical equation, Theory V2, or a causal router
  intervention.
- It does not prove that memory is count-linear or that a model-free latent
  specialization state exists.
- It does not turn six clustered social seeds into response-level replicates.
- It does not authorize more paid calls, a new society, or a probe increase.

## Deliverables and next step

The machine-readable outputs are in
`reports/post-v1-measurement-aware/`: split-half tables, cross-fitted dynamics,
construct-aligned router diagnostics, cross-half exposure, memory ladder,
MICRO stability, sharing timescale, adequacy curve, null simulations, revised
evidence, figures, and raw hash manifest. An erratum corrects the old
interpretation, while the requirements document records constraints for any
future principal-researcher design. A future calibration protocol is draft-only
and not authorized. **NEXT ACTION: PRINCIPAL RESEARCHER REVIEW.**
