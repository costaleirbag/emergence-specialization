# Theory V1 forensic analysis repair report

## Executive result

Theory V1 is **closed** after a deterministic offline forensic reconstruction.
The raw MICRO and canonical restarted MACRO experiments are technically valid
and immutable. The equations were frozen before MACRO, but the original derived
prediction/scorecard implementation was not fully faithful to them. After
repair, the frozen scorecard is:

| Test | Result |
|---|---|
| T1 predictive ordering | FAIL |
| T2 pairwise direction | PASS |
| T3 beta response | FAIL |
| T4 matched effective gain | FAIL |
| T5 sharing law | FAIL |
| T6 capacity law | FAIL |
| T7 criticality | FAIL |
| T8 cross-ecology | FAIL |
| T9 dominant mode | NON_IDENTIFIABLE |

The mechanical global label under the frozen criteria is **NOT SUPPORTED IN
CURRENT FORM**. This is not a claim that the equations are the only possible
model; it is the result of evaluating the already-frozen model without
retrospective tuning.

## Why repair was necessary

The original sealed prediction artifact contains 864 seed-level rows. It uses
the `K` matrix for the loop that emitted a row rather than the row's social
capacity: 576/864 rows have a k/K mismatch. It also reports full-space spectra,
which can include the uniform niche mode excluded by the specialization
definition. These are implementation defects, not theory revisions.

## Raw experiment validity

The canonical MACRO raw log contains 186,368 unique terminal logical calls and
186,393 physical completion attempts. The model is consistently
`deepseek-v4-flash`; technical retries remain attached to their logical IDs.
The auxiliary checkpoint journal has 147,425 rows, while the canonical raw
completions contain all 147,456 expected checkpoint observations. Exactly 31
rows were reconstructed deterministically; 0 were ambiguous and 0 imputed.
The aborted serial run is quarantined and never enters scientific analysis.

## Repaired MICRO K and linearity

The primary interpretation pools all eight independent MICRO seeds per
ecology×capacity. Explicit centered least squares and an independent pairwise
reconstruction agree to numerical precision (maximum discrepancy below
`7e-17`). Pooled K and the arithmetic seed mean also agree below `2e-17` in this
balanced design. Full per-seed matrices and diagnostics are in
`reports/theory-v1/repair/k_reconstruction.json`.

The double-swap diagnostic is poor rather than exact. Mean R² by ecology and
capacity is: V31_FRESH `-1.349, -1.809, -2.366` for k=4,8,12 and
AFFINE_BOOLEAN_V1 `-0.701, -2.391, -3.173`. The complete R², cosine,
normalized error, MAE, and maximum-error table is in
`micro_linearity_diagnostics.csv`. Thus a local K signal can exist without K
being a sufficient linear microscopic model.

## Repaired predictions and centered dynamics

The repaired population table has 36 unique rows. Each row contains the K/T/J
hashes, centered eigenvalues, `R_spec`, `lambda_spec`, predicted growth, regime,
and dominant mode. Uniform niche modes are excluded by construction. The
primary repaired spectrum contains 22 subcritical and 14 transitional cells;
no cell qualifies for the frozen T9 supercritical-plus-gap condition.

## Scorecard details

- **T1:** pooled Spearman `0.6543`, below the frozen `.70` threshold; this is
  not an ordering pass.
- **T2:** 286 eligible within-ecology comparisons, with the frozen directional
  criterion passing.
- **T3:** only 1/6 beta panels reaches the frozen `.70` panel criterion.
- **T4:** the two nominally matched `(1-epsilon)beta` conditions do not have
  mean observed differences within `.002` in both ecologies.
- **T5:** the prescribed private > partial-share > shared law is not recovered
  in both ecologies with the preregistered seed criterion.
- **T6:** the frozen capacity ordering does not correlate at the required
  threshold.
- **T7:** among 22 non-transitional cells, classification accuracy is
  approximately `0.591`, below `.75`.
- **T8:** the combined cross-ecology criterion fails because the major laws and
  ecology-specific support are not all present.
- **T9:** no cell is eligible under the frozen `R_spec > 1.02` and relative-gap
  rule, so the result is non-identifiable rather than a forced failure.

Continuous values, seed-level matrices, and sensitivity interpretations are in
`reports/theory-v1/repair/theory_v1_scorecard_repaired.json` and
`sensitivity_scorecards.json`. No interpretation was selected for predictive
performance.

## Formation versus exploitation

The repaired MACRO competence trajectories and secondary diagnostics may still
show behavioral differentiation, but that does not rescue the frozen
mechanistic scorecard. `Psi_spec` is the formation observable; routing,
matching, and team utility are secondary exploitation diagnostics. They cannot
replace a failed T1–T9 prediction.

## Implementation failure versus theory failure

Implementation defects: wrong K-to-cell assignment, full-space spectral
scoring, incomplete/unsafe scorecard joins, and the auxiliary checkpoint
journal omission. Repaired theory-level failures: weak predictive ordering,
beta/matched-gain mismatch, sharing/capacity-law mismatch, and criticality
classification mismatch. The former are fixed without changing data; the
latter remain evidence against Theory V1 in its frozen form.

## Epistemic status

The repaired result is a **forensic evaluation of the pre-specified
mathematical specification after deterministic implementation repair**. It must
not be described as if the repaired implementation had been sealed before the
MACRO data. Both the equations' prospective seal and the post-MACRO discovery
of code defects are part of the provenance.

No new model calls, credentials, or scientific data were used.
