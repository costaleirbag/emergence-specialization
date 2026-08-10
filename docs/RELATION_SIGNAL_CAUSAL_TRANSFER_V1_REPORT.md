# Relation-Signal Causal Transfer V1

**Status:** post-run report generated only after the frozen 3,456-call campaign.
This experiment is learner-level; it does not test a society.

## Executive result

The final classification, technical health, cost, and R1–R7 gates are copied
from `reports/task-ecology/relation-signal-causal-transfer-v1/analysis_summary.json`
after all logical tasks are terminal. No gate is changed after observing data.

## Scientific question

Does a minimal statement about the relation between source and target policies
change DeepSeek's realized transfer on cross-domain cases, while holding the
semantic history and target case fixed?

The historical V2 cross-domain responses are the no-signal `R_NONE` reference.
The new randomized/interleaved arms are `R0`, truthful-or-counterfactual `RS`,
and truthful-or-counterfactual `RI`. The cue is an intervention on model-visible
context, not evidence that the model inferred a hidden relation.

## What was known before inference

V3.1 supplied the semantic ecology and V2 supplied natural h=8 histories and
held-out probes. The regime-observability audit showed that source histories do
not identify the global geometry; pairwise relation is the missing observable
structure. This campaign therefore tests the next learner-level arrow only:

```text
J_obs / L*_obs  ->  L^DeepSeek
```

## Frozen protocol

- DeepSeek Direct, `deepseek-v4-flash`, thinking off.
- Seeds: 9201–9204; geometries: GLOBAL, BLOCK, DIAGONAL.
- Cross-domain tasks only for new calls: 1,152 underlying tasks × 3 cue arms.
- Eight V2 evaluation probes per target; natural resolved h=8 histories.
- Existing V2 same-family transfer cells are reused only in the truthful-R
  analysis; no same-family calls were added.
- New logical calls: 3,456; technical retry policy: at most one retry.
- Statistical unit: environment seed (`n=4`), not API response.

## Technical health and cost

See `technical_health.json` and `cost.json` for the raw reconciliation. Report
logical coverage, physical attempts, retry categories, semantic OOD count,
model/fingerprint, token usage, and observed configured cost. A valid wrong or
semantic out-of-domain response remains a terminal scientific observation.

## Primary outcomes

The machine-readable outputs contain source-policy adherence `S`, `Gamma_R`,
`Delta_same`, `Delta_independent`, `Upsilon_R`, truthful-R transfer matrices,
`D/O/Q`, BLOCK `W/C/B`, geometry ordering, and relation-oracle alignment. Report
per-seed values before any aggregate mean, median, range, or sample SD.

## Interpretation boundary

Positive cue sensitivity is not proof of latent relation inference: it may arise
from generic context effects, semantic priors, anchoring, or a cue-induced
response policy. Conversely, a null result means only that this intervention did
not control realized transfer under this interface and budget. It does not show
that the ecology lacks information. No society experiment is authorized by any
outcome.

## Required outputs

The authoritative analysis directory is:

`reports/task-ecology/relation-signal-causal-transfer-v1/`

It contains response-level data, seed contrasts, truthful-R matrices, component
and anchoring diagnostics, technical health/cost, alignment tables, figures, and
the frozen manifest. The final package and checksum are created only after
offline analysis and final tests complete.

## Next scientific question

After principal-researcher review: does the measured cue-controlled transfer
justify a separately preregistered society experiment, or is a cheaper learner
mechanism diagnostic required? This report does not answer that question by
itself.
