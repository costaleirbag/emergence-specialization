# HSE robustness audit

**Status:** offline sensitivity analysis of clean v2; behavioral-diversity claim
only.

The preregistered/source-compatible measure remains cosine distance with single
linkage. Sensitivity checks recomputed the same hierarchical partition-entropy
area for all 120 clean-v2 behavioral matrices under:

- cosine, normalized Hamming, and success-set Jaccard distances;
- single, complete, and average linkage;
- all 40 probes, leave-one-probe-out, and paired probe bootstrap.

The native cosine/single computation reproduces stored normalized HSE to maximum
absolute error `1.67e-16`.

## Endpoint result

Across all 18 distance/linkage/router combinations, mean `private - shared` HSE
at t=20 is positive.

| Distance | Linkage | Confidence delta | Random delta |
|---|---|---:|---:|
| cosine | single | +0.267 (8/10 positive seeds) | +0.257 (9/10) |
| cosine | complete | +0.295 (8/10) | +0.302 (9/10) |
| cosine | average | +0.290 (8/10) | +0.276 (9/10) |
| Hamming | single | +0.096 (9/10) | +0.084 (10/10) |
| Hamming | complete | +0.116 (9/10) | +0.104 (10/10) |
| Hamming | average | +0.108 (9/10) | +0.094 (10/10) |
| Jaccard | single | +0.266 (8/10) | +0.264 (9/10) |
| Jaccard | complete | +0.266 (8/10) | +0.271 (9/10) |
| Jaccard | average | +0.272 (8/10) | +0.266 (9/10) |

At t=0, every configuration is slightly shared-favoring on average; by t=10,
all endpoint families are private-favoring. This temporal reversal is consistent
with developmental divergence, not a preexisting label preference.

## Probe sensitivity

- In 1,000 joint paired bootstrap resamples of probe indices, the 95% interval
  for the mean endpoint contrast stayed above zero in every configuration.
- `P(mean delta > 0)` was 1.0 in those measurement bootstraps.
- Removing each probe in turn preserved a positive mean endpoint contrast in
  40/40 deletions for every configuration.

These resamples test measurement-item robustness. They do **not** create new
independent societies or justify treating 40 probes as the experimental unit.
The scientific unit is the paired seed (`n=10` per router).

## Interpretation boundary

The qualitative observation that private clean-v2 societies are more
behaviorally diverse than shared societies at t=20 is not an artifact of single
linkage, cosine distance, or one probe item. Hamming and Jaccard are sensitivity
checks, not replacements for the frozen primary HSE.

Robust behavioral diversity still does not establish competence acquisition,
routing alignment, useful division of labor, or anchoring as the causal
mechanism.

