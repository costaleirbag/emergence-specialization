# Theory V1.1 — final harness-clean replication

## Executive result

**THEORY V1.1: CORE THEORY V1 MECHANISM NOT SUPPORTED UNDER CLEAN HARNESS.**

The known concrete-answer-vector prompt confound was removed before this
prospective V1.1 campaign. Stage A passed all five instrument gates, MICRO
completed and sealed the predictions, and the principal researcher authorized
the MACRO under a budget-only increase from US$4.00 to US$5.00. The fresh MACRO
then completed its exact frozen 62,976-call design. The four targeted V1.1
mechanistic tests all failed their preregistered criteria.

This is a clean targeted negative replication of the central V1 mechanism. It
does not define Theory V2, alter Theory V1 equations, or authorize another paid
experiment.

## Provenance and freeze

- Provider: DeepSeek Direct; model `deepseek-v4-flash`; thinking off.
- Prediction seal: `theory-v1-1-predictions-sealed-20260813`.
- Prediction SHA-256: `ee88d43e3e47e11bf068510e37411832c95010a3012b9b9a491981e839062adb`.
- MACRO manifest: `reports/theory-v1-1/macro_manifest.json`.
- MACRO logical calls: 62,976 exactly (two ecologies × six seeds × eight cells).
- Scientific cells and seeds were not changed after sealing.
- Stage A + MICRO + MACRO observed cost: US$3.2363886104; hard ceiling US$5.00.

The original US$4.00 stop and the later budget-only amendment are both retained
in the execution log. The amendment was based on cost forecast, not MICRO
scientific values.

## Harness validation and MICRO

Stage A used 1,024 calls and passed HV1–HV5. The pooled frequency of `[0,1,0]`
was 0.1134 and the modal output frequency was 0.1887, so the historical exact
answer-vector collapse was not reproduced. Pooled local plasticity was
`G_abs(8)=0.109375` and `G_rel(8)=0.116881`.

MICRO used 19,584 calls (cost US$1.1331386304), with six fresh seeds per ecology
and pooled K estimation. The two K estimators agreed to 1.11e-16. The weak
double-swap linearity diagnostic remains descriptive and did not gate MACRO, as
specified by the protocol.

## MACRO technical health

Raw terminal coverage is complete: 62,976 unique terminal logical IDs from
62,995 physical attempts. There were 19 technical retries: 12 transient
transport, 5 parse, and 2 empty-content attempts. Eight semantic out-of-domain
responses remained valid incorrect observations and received no scientific
second chance. All terminal provider metadata report `deepseek-v4-flash` and a
single fingerprint.

The auxiliary checkpoint journal has 48,573 rows; 49,152 were expected. The
579 absent journal rows were reconstructed exactly from terminal raw events in
`macro/checkpoint_reconstruction.csv`. The canonical scientific analysis uses
the raw completion log, not the incomplete auxiliary journal. No raw event was
rewritten and no inference was rerun.

The runner emitted a late string-cell-ID finalization exception after raw
coverage reached 62,976. This did not create duplicates or missing logical
observations; it is recorded as an infrastructure defect in the technical
provenance. The raw audit, not the runner's final print status, is the source of
truth for completion.

## Frozen tests and results

Growth is the preregistered OLS slope of `log(Psi_bit(t)+1e-6)` at
`t={16,32,64}`. The independent unit is the ecology × social seed; the six
seeds are not treated as thousands of independent probe responses.

| Test | Frozen criterion | Result |
|---|---|---|
| V11-A adaptive ordering | pooled Spearman ≥ .70 and both ecology panels ≥ .50 | **FAIL** — pooled 0.0366; V31 −0.3000; AFFINE −0.8000 |
| V11-B matched gain | `abs(mean(C2−C5)) ≤ .002` in each ecology | **FAIL** — V31 +0.00779; AFFINE +0.00564 |
| V11-C sharing | predicted q ordering in both; private>full-sharing ≥5/6 | **FAIL** — V31 3/6, AFFINE 1/6; ordering absent in both |
| V11-D adaptive amplification | positive C3−C0 mean and ≥5/6 positive in each ecology | **FAIL** — V31 +0.000636, 4/6; AFFINE −0.012025, 0/6 |

The per-seed values and all intermediate matrices are in
`reports/theory-v1-1/macro/growth_by_seed.csv` and
`reports/theory-v1-1/scorecard/v11_scorecard.json`.

## Interpretation

Removing the concrete answer anchor validated the instrument and recovered a
small local-learning signal in Stage A, but it did not recover the predicted
social transfer laws. The result is therefore not explained by the known static
schema anchor alone. The negative result is targeted: it concerns adaptive
ordering, matched beta/epsilon gain, sharing, and adaptive amplification under
the frozen V1 reduction. It does not retest the old capacity, criticality, or
dominant-mode claims.

The result also does not establish that DeepSeek cannot learn any semantic
procedure. It establishes that this clean learner/ecology/social setup did not
realize the frozen V1 mechanism at the tested horizon and seed scale.

## Strongest caveats

1. Six social seeds per ecology make this a bounded qualification/replication,
   not a high-powered estimate of small effects.
2. One provider completion per logical prompt leaves provider stochasticity in
   the seed-level variation.
3. `Psi_bit` is reconstructed from 8 held-out probes per agent-niche cell; it is
   an exact protocol measure but still a noisy finite-support estimate.
4. The late finalization exception and incomplete auxiliary journal show that
   runner bookkeeping needs repair even though raw scientific coverage is
   complete.
5. The comparison against historical V1 is descriptive only; old and new data
   are not pooled as one confirmatory sample.

## Epistemic status and next action

Theory V1 remains frozen and historical; V1.1 is a clean targeted replication
that ends with the negative verdict above. No Theory V2 is defined. No further
paid calls, prompt tuning, model change, or society run is authorized by this
result.

**NEXT ACTION: PRINCIPAL RESEARCHER REVIEW.**
