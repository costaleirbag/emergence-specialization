# Theory V1.1 execution log

## Pre-inference seal

- Timestamp: 2026-08-13
- Branch: `research/developmental-dynamics`
- Starting implementation HEAD: `0729e9497e5928032d332be916e504be4b1c4e93`
- Protocol: `THEORY-V1.1-HARNESS-CLEAN`
- Stage A manifest: `reports/theory-v1-1/stage_a_manifest.json`
- Stage A manifest hash: `49542a0c8b13e65557c4661b1e8606b95a1c08b1a25b33278a4fd97bafcec205`
- Stage A tasks hash: `081ef9e3d80521d2f7e5223781d2abc93c8ace61bb5535a32dcbb3d6f65f8e52`
- Stage A logical calls: `1,024`
- Fresh-seed collisions: `0`
- Static concrete answer vectors: `0`
- Provider/model: DeepSeek Direct / `deepseek-v4-flash`
- Thinking: off
- Hard new inference ceiling: US$4.00
- Forecast including 50% safety margin: US$3.7675353991
- Forecast decision: PROCEED
- Tests before inference: full suite 274 OK; compileall OK
- External calls before Stage A: `0`

Stage A is the only currently authorized paid action. It must stop before MICRO
if any HV1–HV5 gate fails. No scientific result may alter the frozen seed sets,
task construction, or subsequent conditional protocol.

## Stage A technical closure

- Stage A status: `PASS` (all HV1–HV5 true)
- Stage A logical completions: `1,024 / 1,024`
- Stage A physical attempts: `1,025`
- Stage A technical retries: `1`
- Stage A parse failures: `0`
- Stage A observed cost: US$0.0355964336
- Stage A max active requests: `3` under configured global cap `32`
- Stage A raw events: `data/auto-research/theory-v1-1/stage_a_events.jsonl`
- Stage A gate artifact: `reports/theory-v1-1/harness_validation/harness_gate_results.json`
- Interpretation: instrument-validity gate only; no Theory V1 mechanistic claim is
  inferred from these values.

## MICRO pre-inference reseal

- MICRO implementation commit: `f8613260882dd519809aeb0a5b3b87ed7ba407dc`
- MICRO manifest: `reports/theory-v1-1/micro_manifest.json`
- MICRO manifest SHA-256: `de847f3089f22da61eaf486d6d3a8f3d5d5fc523d47bc6ce1b446504397b5895`
- MICRO tasks hash: `0f757f6b55e47c84ed3581c93e8f7b30e97fb46fb5afb81a74ca4f578334007a`
- MICRO logical calls: `19,584`
- MICRO seed collisions: `0`
- MICRO paid execution: started only after full suite `275 OK` and compileall OK.
- MICRO raw namespace: `data/auto-research/theory-v1-1/micro_events.jsonl`

## MICRO closure and MACRO stop

- MICRO status: `completed`, `19,584 / 19,584` logical calls
- MICRO physical attempts: `19,588`
- MICRO technical retries: `4`
- MICRO observed cost: US$1.1331386304
- Stage A + MICRO observed cost: US$1.1687350640
- Prediction rows sealed: `16` (8 cells × 2 ecologies)
- Prediction seal tag: `theory-v1-1-predictions-sealed-20260813`
- Post-MICRO projected MACRO cost: US$2.7389706913
- Projected total without margin: US$3.8721093217
- Projected total with frozen 30% remaining safety margin: US$4.6938005292
- Hard ceiling: US$4.00
- MACRO status: `BLOCKED BEFORE MACRO` by the explicit budget guard
- MACRO logical calls executed: `0`

## Budget amendment and MACRO closure

- Amendment: principal-authorized budget-only increase from US$4.00 to US$5.00.
- Amendment commit: `14c4f21`; tag: `theory-v1-1-budget-amended-20260813`.
- Scientific observations available at amendment: `0`.
- Prediction seal SHA-256 before MACRO: `ee88d43e3e47e11bf068510e37411832c95010a3012b9b9a491981e839062adb`.
- MACRO logical completions: `62,976 / 62,976`.
- MACRO physical attempts: `62,995`; technical retries: `19`.
- Retry categories: transient transport `12`, parse `5`, empty content `2`.
- Semantic out-of-domain observations: `8`; no scientific retry was applied.
- MACRO observed cost: US$2.0676535464.
- Stage A + MICRO + MACRO observed cost: US$3.2363886104.
- Model/backend: DeepSeek Direct / `deepseek-v4-flash`; one provider fingerprint.
- MACRO raw SHA-256: `582ca0ad1c3d603061c515901f3674a51afcc64cfe365e1967fbbb65c710fe0a`.
- Checkpoint auxiliary raw SHA-256: `2a78d117ddbdb0a8bc98ebd0c7bdf8c54583316c3aa8b335572730486ce570d2`.
- Checkpoint journal: `48,573` present of `49,152` expected; `579` reconstructed exactly from canonical raw completions.
- Raw terminal IDs: unique, complete, no duplicates.
- Technical anomaly: a late `ValueError` on string cell ID `C0` occurred after raw coverage was complete; it did not change logical observations and is not a scientific result.
- V11-A: FAIL (pooled Spearman `0.036585`; V31 `-0.300000`; AFFINE `-0.800000`).
- V11-B: FAIL (mean C2−C5 V31 `+0.007791`; AFFINE `+0.005642`; tolerance `.002`).
- V11-C: FAIL (private>full-sharing V31 `3/6`, AFFINE `1/6`; ordering absent in both).
- V11-D: FAIL (C3−C0 V31 mean `+0.000636`, `4/6`; AFFINE mean `-0.012025`, `0/6`).
- Final verdict: **CORE THEORY V1 MECHANISM NOT SUPPORTED UNDER CLEAN HARNESS**.
- No Theory V2, no additional paid experiment, and no society run.
