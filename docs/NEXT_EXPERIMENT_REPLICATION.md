# Next experiment: five-seed private/shared replication

## Question

Can behavioral diversity emerge reproducibly from initially homogeneous LLM
societies when interaction histories are allowed to diverge?

The immediate target is temporal behavioral differentiation (`B(t)`), not a
claim that private memory is better or that specialization has already been
established.

## Design

- Five paired seeds: `1, 2, 3, 4, 5`.
- Conditions: `private` and `shared` only.
- Four agents, twenty interaction rounds.
- Same DeepSeek V4 Flash model, prompt, task generator, router, memory budget,
  parser, retry policy, concurrency, code commit, and fixed probe set.
- Only feedback distribution differs.
- No probabilistic locality, interventions, epsilon exploration, population
  changes, topology, or minimal-model fitting.

## Checkpoint choice

With four agents and forty probes:

| Schedule | Interaction | Probe | Nominal/run | Retry ceiling/run | Nominal/10 runs |
|---|---:|---:|---:|---:|---:|
| `[0,20]` | 80 | 320 | 400 | 800 | 4,000 |
| `[0,10,20]` | 80 | 480 | 560 | 1,120 | 5,600 |
| `[0,5,10,15,20]` | 80 | 800 | 880 | 1,760 | 8,800 |

The first replication uses **`[0,10,20]`**. It adds one temporal midpoint while
avoiding the five-checkpoint cost and latency explosion. Cheap online observables
are still reconstructed at every interaction round. Schedule C remains a later
option if B shows a meaningful trajectory that needs finer temporal resolution.

## Primary outcome

Normalized HSE trajectory and baseline-relative change:

\[
\Delta HSE_s(t) = HSE_s(t)-HSE_s(0).
\]

For each paired seed:

\[
D_s(t) = \Delta HSE_{private,s}(t)-\Delta HSE_{shared,s}(t).
\]

Report all five `D_s(t)` values. Do not replace them with a significance claim
based on `n=5`.

## Secondary diagnostics

- utilization entropy and effective utilized-agent count;
- routing concentration and switching;
- memory counts and inequality;
- task-agent association/MI (with the seeded null diagnostic when sample size is
  adequate);
- competence matrices, best-individual accuracy, and oracle gain at checkpoints;
- raw-label occupancy only as an exchangeability sanity check.

HSE increase means behavioral differentiation. It does **not** by itself imply
specialization or useful division of labor.

## Success and ambiguity

Success for this phase means obtaining technically valid paired runs and seeing
whether the qualitative seed-1 private/shared contrast reproduces across seeds.
There is no arbitrary HSE threshold.

All of these are informative outcomes:

- private approximately equals shared;
- large seed variance;
- both conditions differentiate;
- neither condition differentiates;
- private changes HSE without structured routing or complementarity.

## Health gate

Before using a run in paired analysis, run the offline health summary. A run is
`healthy` only when every expected logical completion succeeds without errors.
Retries, partial usage, or any missing logical completion produce `warning` or
`invalid` according to the documented policy. Invalid runs are not silently
excluded; preserve them and report them as infrastructure outcomes.

The previous seed-1 artifacts show why this gate matters: the latest private
run had 398/400 successful logical completions, and the latest shared run had
386/400, with many timeouts and stream/chunk errors. Those artifacts are useful
diagnostics but are not a clean matched replication pair under the strict gate.

## Reproducibility

The batch planner records the git commit, batch/config hashes, system-prompt
hash, probe-set hash, effective task/router/feedback seeds, model, backend,
expected OMP version, checkpoints, call counts, and retry ceiling before any run
is started. The explicit `--run --confirm-real` mode executes pairs
sequentially; it skips only artifacts passing the strict `healthy` health gate,
so a process that exited `completed` with missing logical calls is not silently
treated as resumable data.
