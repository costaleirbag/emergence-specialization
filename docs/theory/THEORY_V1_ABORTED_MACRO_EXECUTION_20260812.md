# Theory V1 aborted MACRO execution — 2026-08-12

## Status

**ABORTED FOR INFRASTRUCTURE / THROUGHPUT.** This is a quarantined technical
artifact, not a Theory V1 confirmatory dataset.

The initial MACRO executor serialized the 288 independent ecology × seed × cell
trajectories. The principal researcher authorized stopping it and restarting
from the frozen protocol after an infrastructure-only concurrency repair.

## Technical state at shutdown

| quantity | value |
|---|---:|
| logical terminal completions | 3,712 / 186,368 |
| physical attempts | 3,716 |
| technical retries | 4 |
| semantic out-of-domain observations | 6 |
| parsing errors | 4 |
| model | `deepseek-v4-flash` |
| observed cost | US$0.123065488 |
| provider identity | unchanged in health metadata |

The process exited on a missing-usage/cost error while processing a checkpoint.
Its persisted events were preserved before quarantine. No scientific metrics,
cell accuracies, regimes, predictions, or scorecard quantities were inspected
before the abort. The partial responses are therefore usable only for
throughput/latency and infrastructure diagnostics.

## Quarantine policy

The raw files are preserved at
`data/quarantine/theory-v1-macro-aborted-serial-run-20260812/` and hashed in
`SHA256.json`. They must never enter the Theory V1 scorecard, scientific figures,
effect estimates, or confirmatory sample.

The restarted MACRO uses the same frozen manifest, seeds, task streams, prompts,
and sealed predictions, but begins with empty canonical event logs.
