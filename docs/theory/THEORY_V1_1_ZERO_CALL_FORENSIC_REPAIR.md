# Theory V1.1 zero-call forensic repair

Before any V1.1 inference, the historical Theory V1 scorecard implementation
was audited and repaired offline. Raw MICRO/MACRO observations, frozen
equations, thresholds, prediction seal, and old closure were not changed.

## Repairs

- T3 now filters exactly `beta={0,4,8,12,20}`, `epsilon=.10`, `q=0`; the
  matched-gain `beta=16, epsilon=.55` cell is excluded.
- T4 pairs the two matched-gain cells by `(ecology, social seed)`, never by
  `cell_id`.
- T5 uses the actual eight seed-level observations per ecology and reports
  private-vs-shared counts in `0..8`.
- T6 consumes the complete private `k×beta` grid: 2 ecologies × 3 capacities ×
  5 beta values = 30 cells.
- Spearman uses conventional average ranks for ties.
- Sensitivity scoring is write-isolated from primary prediction/scorecard
  artifacts.

## Corrected historical continuous values

The repaired scorecard remains `NOT SUPPORTED IN CURRENT FORM`, but the
corrected numbers are now:

- T1 pooled Spearman: `0.6568824071`.
- T2: PASS, 286 eligible comparisons.
- T3: FAIL, 2/6 panels pass.
- T4: FAIL; mean paired differences V31 `0.0165228`, AFFINE `0.0131138`.
- T5: FAIL; private > full-sharing seed count is 5/8 in each ecology, and
  the complete mean ordering is not recovered.
- T6: FAIL; 30 eligible cells, Spearman `0.5641255605`.
- T7: FAIL, 22 eligible cells, accuracy `0.5909091`.
- T8: FAIL.
- T9: NON_IDENTIFIABLE.

These are corrected evaluations of the historical harness-confounded Theory V1
experiment, not new scientific data and not a Theory V2 result.

## Harness-clean instrument status

The V1.1 neutral output instruction has been implemented in separate source
constants. Static instructions contain no complete valid three-bit vector, and
the anti-regression tests inspect all eight possible vectors. No paid calls
have been made. Stage A remains pending principal-authorized execution after
the local commit and preregistration.
