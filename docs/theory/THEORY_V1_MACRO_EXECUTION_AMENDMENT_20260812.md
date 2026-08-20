# Theory V1 MACRO execution amendment — 2026-08-12

## Reason

The original confirmatory executor serialized independent trajectories and was
computationally impractical. This amendment changes orchestration only.

## Scientific state available at decision time

Only technical health metadata was used: completions, attempts, retries,
semantic OOD count, parsing count, cost, latency/throughput, and model identity.
No regime-level scientific output was inspected.

## Scientific protocol changes

**None.** The equations, MICRO data, K estimates, sealed predictions, ecologies,
seeds, task streams, memory/router rules, checkpoints, prompts, model, and
scientific retry semantics remain frozen.

## Infrastructure changes

- t0 evaluations are gathered with bounded concurrency;
- the 288 independent ecology × seed × cell trajectories run concurrently;
- online state transitions remain strictly sequential within each trajectory;
- checkpoint probes use an immutable state snapshot and are read-only;
- t0, online, and checkpoint requests share one global request gate of 32;
- events are keyed by logical IDs and scientific indices, not arrival order;
- the partial serial run is quarantined and never resumed or mixed into the restart.

The deterministic offline mock protocol must produce identical canonical states
under concurrency 1 and 32, while demonstrating overlap greater than one. The
existing frozen prediction tag is not modified. A new execution reseal tag will
identify the infrastructure commit before the restarted paid run.

## Accounting

The aborted MACRO cost remains real and is recorded separately from MICRO and
the restarted MACRO. The US$8.00 Theory V1 hard ceiling remains active.
