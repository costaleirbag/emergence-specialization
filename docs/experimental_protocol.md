# Experimental protocol

## Baseline invariants

The scientific baseline uses identical host-side agents, one fixed hidden-world
task per interaction round, a confidence router, Python-owned memory, and fresh
provider sessions. The private and shared controls must use the same seed,
task sequence, probe-set hash, model, prompt, decoding metadata, number of
agents, rounds, checkpoints, and retry policy. They differ only in feedback
recipients.

The fixed probe set is evaluated at checkpoints and never updates memory. Raw
run directories (`metadata.json`, `events.jsonl`, `metrics.jsonl`,
`summary.json`) are immutable scientific inputs; reports and trajectories are
derived offline.

## Call accounting

For a run with `N` agents, `T` interaction rounds, `K` checkpoints, and `P`
probes:

```text
interaction calls = T × N
probe calls       = K × P × N
nominal calls     = interaction + probe
retry ceiling     = nominal × (technical_retries + 1)
```

The batch planner reports these numbers without executing anything.

## Cheap versus expensive measurements

`metrics.online.online_observables` reconstructs cumulative routing counts,
utilization entropy, routing concentration, selected accuracy, confidence
statistics, memory counts/inequality, switching, and task-agent MI from normal
interaction events. These are candidates for every-round monitoring.

HSE, behavioral matrices, competence matrices, and oracle gain remain probe
derived. Their call cost should be reported explicitly and checkpoints should
be scheduled deliberately (`checkpoints: {every: 5}` or an explicit list).

## Multi-seed analysis

Use `emergent_specialization.batch --plan` to expand a batch. Use
`emergent_specialization.aggregate` only after runs are complete. Do not average
agent columns across seeds without `metrics.permutation` alignment. Labels are
opaque and exchangeable.

## Statistical sanity

The MI null helper is a seeded permutation diagnostic for small samples. It is
not a universal p-value and should not be used alone to claim emergence.

