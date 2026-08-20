# Theory V1 MICRO parameterization report

## Status

**NOT RUN — blocked before paid inference.** This is a preflight record, not a
scientific result. No `K` matrix, spectrum, social prediction, or Theory V1
score exists yet.

## Frozen design

The MICRO manifest contains 2 ecologies × 8 fresh seeds × 3 capacities and 544
logical completions per ecology×seed×k: one balanced baseline, twelve one-slot
swaps, four double swaps, four target niches, and eight held-out probes. Total:
**26,112 logical completions**.

## Cost gate

Recent real DeepSeek Direct semantic-task costs were US$0.0555897104/2,176,
US$0.0406882448/1,920, US$0.0653269344/2,944, and US$0.089407/3,456. Their
mean is US$0.0000236996181 per completion. The full frozen Theory V1 design is
212,480 logical completions (26,112 MICRO + 186,368 MACRO), forecasting
US$5.0356949 before retries and **US$6.5464033 with the required 30% safety
margin**, above the hard US$6.25 ceiling.

Representative actual rendered h=8 prompts were 2,849 characters for
`V31_FRESH` and 2,147 for `AFFINE_BOOLEAN_V1`; no credential or model call was
needed to measure them.

Therefore the correct action is to stop before paid inference. The protocol is
not reduced, the beta grid is not changed, and no seed/ecology is dropped.

## What is ready offline

- frozen equations and derivation;
- exact epistemic ledger and prediction registry;
- deterministic ecology and micro manifests;
- K estimators and mock superposition/spectrum checks;
- call-count and scoring helpers.

If the principal researcher later authorizes a higher budget or a separately
approved redesign, MICRO must run first, predictions must be sealed, and only
then may MACRO begin.
