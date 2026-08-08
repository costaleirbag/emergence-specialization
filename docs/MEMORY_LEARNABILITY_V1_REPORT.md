# Memory learnability v1 — overnight calibration report

**Status: calibration complete; offline measurement report only.** This is not a
new society run and is not evidence that specialization emerged.

## Protocol and provenance

- Protocol: `memory-learnability-v1`
- Model/backend: `deepseek-v4-flash` through DeepSeek Direct; thinking off
- Frozen base: `configs/research/v2/clean_confidence_private_20.yaml`
- Worlds: ALPHA, BETA, GAMMA, DELTA; fixed probe hash
  `cb234422389ff7d5a04566112a483f147e4a3d1212b1c69fbb0396ec9ca4c55e`
- Same-world memory sizes: `k = 0, 1, 2, 4, 8`
- Controls: corrupted labels, unrelated world, and two examples/world mixed memory
- 10 context seeds/world, 10 held-out probes/world, 3 repeated calls/query context
- No router, feedback, multi-agent state, or memory mutation by probes

The real calibration used exactly 9,600 logical queries and 9,669 physical
attempts. It completed at an observed cost of **US$0.398420**, below the
authorized US$1.00 cap. The provider fingerprint was constant in all successful
records. There were 69 recovered attempts (66 empty-content and 3 technical
parse failures), no rate-limit/server errors, and no missing token-usage records.
Observed latency across attempts was mean 2.041 s, median 2.025 s, minimum
0.844 s, maximum 7.390 s. Raw append-only data are in
`data/calibrations/memory-learnability-v1/`.

## Descriptive learnability results

| Context | k | Mean accuracy | Mean confidence | Brier | Confidence AUC |
|---|---:|---:|---:|---:|---:|
| same world | 0 | 0.192 | 0.149 | 0.162 | 0.568 |
| same world | 1 | 0.150 | 0.743 | 0.602 | 0.418 |
| same world | 2 | 0.171 | 0.735 | 0.544 | 0.489 |
| same world | 4 | 0.145 | 0.642 | 0.478 | 0.453 |
| same world | 8 | 0.172 | 0.641 | 0.459 | 0.523 |
| corrupted k=8 | 8 | 0.150 | 0.259 | 0.223 | 0.464 |
| unrelated k=8 | 8 | 0.174 | 0.317 | 0.244 | 0.468 |
| mixed k=8 | 8 | 0.170 | 0.724 | 0.532 | 0.453 |

The immediate engineering conclusion is that this frozen prompt/model pair did
not show a monotone same-world accuracy curve in this calibration. Memory
affected confidence and output behaviour, but the measurement does not support
assuming that `recent_k=8` reliably teaches the hidden rule. In particular, high
confidence in the memory conditions was not a reliable correctness signal. This
is precisely why the calibration was run before authorizing a new scientific
condition.

The repeated-call diagnostic contains 320 contexts × 30 probe-level responses.
Answer agreement and confidence variance are in
`reports/calibrations/memory-learnability-v1/replicate_reliability.csv`; these
records should be used to quantify stochasticity rather than treating a single
completion as a deterministic capability measurement.

## Controls and positive control

The corrupted-label, unrelated-world, and mixed-memory arms are negative/control
conditions for interpretation. They are not ablations of the society dynamics.
`synthetic_positive_control.json` is an explicitly constructed analysis-only
specialist matrix. It yields `eta_route = 1` and positive matching gain by
construction; it is labelled **SYNTHETIC POSITIVE CONTROL — NOT SOCIETY DATA**.
It verifies that the offline metrics can recognize a deliberately supplied
competence pattern, not that the LLM generated one.

## Reproducible offline commands

```bash
PYTHONPATH=src .venv/bin/python -m emergent_specialization.memory_learnability_report
PYTHONPATH=src .venv/bin/python -m emergent_specialization.overnight_offline
```

These commands read local artifacts only and make no provider calls.

## Decision gate

Do not interpret this calibration as a failed society experiment. It is a
measurement gate: before running another society condition, decide whether the
current prompt/memory protocol is sufficiently learnable to make a private/shared
developmental comparison meaningful. Any change to prompt, memory budget, model,
worlds, or task protocol is a new pre-registered protocol and must not be mixed
with clean v2.
