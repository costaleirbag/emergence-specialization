# Theory V1 MACRO resume and checkpoint repair — 2026-08-12

## Finding

An execution-only audit of the interrupted canonical journal found that the
original concurrent executor had completed post-online probes only at checkpoint
128. The frozen schedule is `(0, 16, 32, 64, 128)`, so checkpoints 16, 32, and
64 were absent. The same audit found that its resume path replayed persisted
online state before restarting the loop, which could make a resumed trajectory
begin a new step from a later state.

These findings used only event identity/type/checkpoint metadata and counts; no
scientific accuracy, regime, prediction, or scorecard output was inspected.

## Repair

The executor now:

1. constructs a fresh state per trajectory on every invocation;
2. replays persisted online steps in scientific-time order within that
   trajectory only;
3. evaluates every frozen checkpoint immediately after its state (`16, 32, 64,
   128`) is reconstructed or newly reached;
4. evaluates each checkpoint from an immutable memory snapshot and asserts the
   scientific state hash is unchanged afterwards;
5. fills only missing logical checkpoint IDs on resume, without duplicating any
   completed logical completion.

The repair restores the frozen protocol; it does not change its checkpoints,
tasks, prompts, truth function, router, memory rule, seeds, predictions, or
metrics. A deterministic fake-backend test verifies that a split/resumed
trajectory reaches the exact serial final state and fills all four checkpoint
sets without state mutation.
