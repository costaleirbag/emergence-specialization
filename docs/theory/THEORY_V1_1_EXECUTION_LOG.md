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
