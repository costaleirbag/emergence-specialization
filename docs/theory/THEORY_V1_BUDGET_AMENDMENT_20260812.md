# Theory V1 — principal-researcher budget amendment and reseal

## Scope

This is an operational amendment only. It changes the hard external inference
ceiling from **US$6.25** to **US$8.00** so the already-frozen prospective
challenge can be run with its required safety margin. It does not change the
scientific protocol.

Before this amendment:

- MICRO completions: 0
- MACRO completions: 0
- prospective DeepSeek calls: 0
- prospective scientific observations: 0

## Frozen accounting

The unchanged design remains:

- MICRO: 26,112 logical completions
- MACRO: 186,368 logical completions
- total: **212,480 logical completions**

The current prompt-based forecast is US$5.0356949. Applying the original 30%
safety margin gives US$6.5464033, which is below the amended US$8.00 ceiling.

The forecast is operational only. It does not authorize unrelated experiments,
scientific reductions, seed changes, ecology changes, or post-hoc tuning.

## Scientific invariants

The following remain byte-for-byte protocol commitments: Theory V1 equations,
the `K` definition and retention model, `J`, `R_spec`, specialization and T1–T9
scorecard, thresholds, ecologies, seeds, MICRO/MACRO designs, beta/epsilon/q/k
grids, checkpoints, probe counts, task horizon, and call counts.

## Reseal provenance

The previous protocol seal was `theory-v1-protocol-sealed-20260812`. Its only
post-seal implementation difference was the explicit scorecard helper and its
tests; these were added before any prospective inference and do not change the
protocol or scientific quantities. This amendment records that diff and makes
the current commit the active protocol seal. The old freeze and seal tags are
not moved, rewritten, or deleted.

The new active seal is `theory-v1-protocol-resealed-20260812`.

## Execution gates

MICRO must complete and pass technical/K-estimation integrity checks before
predictions are generated. Predictions must be committed and immutably sealed
before MACRO begins. After MICRO, the remaining MACRO cost is reforecast from
actual usage; if the actual MICRO cost plus 1.30 times the projected remaining
MACRO cost exceeds US$8.00, execution stops before MACRO and returns to review.

No scientific interpretation may determine whether to continue. Only budget,
provider identity, manifest/hash integrity, raw-log integrity, or systematic
technical failure can stop the frozen campaign.
