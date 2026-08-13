# Theory V1.1 harness-clean replication preregistration

This preregistration is frozen before any V1.1 model inference. It changes the
instrument only; Theory V1 mathematics and interpretation remain frozen.

## Hypothesis and status

The experiment discriminates a historical concrete-answer harness failure from
failure of the frozen V1 mechanism. Historical V1 is prospective but
harness-confounded. Stage A is instrument validation, MICRO is parameterization,
and targeted MACRO is confirmatory only if the preceding stages pass.

## Static harness

Provider: DeepSeek Direct. Model: `deepseek-v4-flash`. Thinking: off. Responses
must be a JSON object with one `decisions` key containing exactly three binary
integers. No complete answer vector occurs in static instructions. Resolved
labels may occur only as natural feedback history.

## Stage A

Seeds are fixed: V31 `94101–94104`; AFFINE `95101–95104`. Each ecology×seed is
evaluated at `h=0`, same-niche `h=4`, same-niche `h=8`, and foreign-niche `h=8`,
with four target niches and eight held-out probes: exactly 1,024 logical calls.

HV1: `[0,1,0]` fraction < 0.50. HV2: modal vector fraction < 0.70. HV3:
pooled absolute and relative local gain > 0. HV4: same-h8 beats baseline in at
least 6/8 ecology×seed units. HV5: correct model/backend and parse failure ≤2%.
Any failure stops before MICRO; no prompt tuning follows.

## MICRO and targeted MACRO (conditional)

If Stage A passes, fresh MICRO seeds are V31 `96101–96106` and AFFINE
`97101–97106`, exactly 19,584 calls using the unchanged 544-call per
ecology×seed×k design. Predictions are sealed before MACRO. Fresh social seeds
are V31 `98101–98106` and AFFINE `99101–99106`; the eight k=8 cells C0–C7 are
fixed in `THEORY_V1_1_HARNESS_CLEAN_PROTOCOL.md`, for exactly 62,976 MACRO
calls. No memory-capacity, criticality, or dominant-mode claim is retested.

## Confirmatory questions

V11-A: tie-aware Spearman for private beta `{0,4,8,12,20}`, pooled ≥.70 and
both ecologies ≥.50. V11-B: matched-gain mean difference ≤.002 in each ecology.
V11-C: frozen q ordering in both ecologies and private > full-sharing in at
least 5/6 seeds per ecology. V11-D: beta=12 versus beta=0 private positive
paired mean and positive in at least 5/6 seeds per ecology.

The clean-support verdict requires V11-A plus at least two of B–D. Otherwise
the result is MIXED or CORE THEORY V1 MECHANISM NOT SUPPORTED UNDER CLEAN
HARNESS. No automatic Theory V2 or follow-up inference is authorized.

## Budget and provenance

Hard new inference ceiling: US$4.00. Forecast and 50% safety margin must be
below the ceiling before Stage A. Stage reforecasts use technical usage/cost
only. V1.1 artifacts are isolated under `reports/theory-v1-1/` and
`data/auto-research/theory-v1-1/`; old V1 raw data are never reused as V1.1
observations.
