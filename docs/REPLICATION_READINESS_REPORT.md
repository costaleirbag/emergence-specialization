# Replication readiness report

> This document records the earlier five-seed planning pass. The current
> first-pair gate, including incomplete-run health handling, mock E2E checks,
> `Phi(t)`, and exact seed-1 commands, is maintained in
> `docs/FIRST_PAIR_READINESS_REPORT.md`.

## Executive summary

**READY FOR REAL REPLICATION: YES, with a mandatory health gate.**

The legacy scientific semantics are preserved and the next batch is prepared as
five paired PRIVATE/SHARED seeds. The previous seed-1 artifacts expose a real
shared-runtime reliability problem, so no run may be interpreted merely because
its process exits with `status=completed`.

## Scientific question

Can behavioral diversity emerge reproducibly from initially homogeneous LLM
societies when interaction histories are allowed to diverge?

The primary target is temporal behavioral differentiation (`B(t)`). HSE is an
observable of behavioral diversity; it is not, by itself, evidence of
specialization or useful division of labor.

## Branch / commit

- Branch: `research/developmental-dynamics`
- Implementation HEAD before this report commit: `9a055aa`
- Final report tip: verify with `git rev-parse HEAD`
- Expected OMP: `omp/17.2.10`
- Probe-set hash: `cb234422389ff7d5a04566112a483f147e4a3d1212b1c69fbb0396ec9ca4c55e`

## Baseline compatibility audit

The diff from `main` was audited semantically:

- **Analysis-only:** online observables, aggregate analysis, permutation
  alignment, MI null diagnostics, HSE deltas, recovery metrics, and health
  summaries.
- **Config/schema extension:** regular checkpoints, feedback locality,
  initial conditions, and opt-in interventions. Existing YAML fields remain
  valid.
- **Experimental runtime behavior:** only opt-in probabilistic feedback,
  schedules, initial conditions, or memory interventions. Legacy private/shared
  configs do not activate any of these.
- **Logging:** additional metadata for opt-in controls and explicit intervention
  events. Existing inference/round/checkpoint records remain readable.
- **Tests/docs:** expanded test suite and research protocol/configuration docs.

The only potentially consequential changes are opt-in extensions. For legacy
configs, `RunConfig.effective_feedback` translates `memory_mode=private/shared`
to the old recipient semantics. Task RNG, router RNG, memory policy, prompt,
probe behavior, parser, retries, OMP command, and metrics are unchanged.

## Core semantic checks

- Agents are initialized as identical host-side wrappers with no IDs in prompts.
- Task generation uses an independent task RNG.
- Router responses are sorted by agent ID before confidence/tie selection; ties
  use the explicit router RNG.
- `asyncio.gather` returns results in submitted agent order; completion order is
  not used for routing.
- `recent_k=8` remains the memory policy.
- Private feedback reaches only the selected agent; shared feedback reaches all.
- Probe evaluation uses frozen snapshots and does not update memory.
- Backend `omp` remains fresh `--mode rpc --no-session` per completion.

The new tests verify that legacy private/shared paired runs generate identical
task sequences, and that reversing response iteration order does not alter tie
selection.

## Old seed-1 pair commit audit

The supplied commits were compared directly:

```text
PRIVATE: 67622182e5f4748fb410c3fb78c8fdbf2d4ceac6
SHARED:  20a3ca3e9abe24e2386b0fd28f31dc4a90ad77db
```

Their difference adds only the Slidev presentation and `.gitignore` entries;
there are no changes to `src/`, configs, tests, prompts, router, memory,
probes, parser, retries, or metrics. The old pair is therefore **effectively
matched with non-scientific differences**. Their task sequences and probe hashes
are equal, and metadata configs match after removing condition/provenance.

However, under the new strict health audit they are not technically clean:

- latest PRIVATE: 398/400 logical completions, 13 timeouts, 1 other error;
- latest SHARED: 386/400 logical completions, 49 timeouts, 2 parse errors,
  14 other errors.

These runs remain preserved as exploratory artifacts, not clean replication
evidence.

## Test results

```text
uv run python -m unittest discover -s tests -v
77 tests: OK
uv run python -m compileall -q src
OK
```

All checks were offline/MockBackend/toy-model checks. Real model calls in this
session: **0**.

## Exchangeability / label-bias audit

PASS for the code-level sanity checks:

- prompts do not contain agent IDs;
- mock fallback is agent-ID independent;
- router explicitly canonicalizes response order;
- ties are reproducible and invariant to input iteration order;
- permutation-invariant summaries and raw-label argmax counts are available.

This is not a formal proof that a remote model has no stochastic process-order
effect. Across future seeds, report raw-label occupancy only as an
exchangeability sanity check, while using permutation-invariant metrics as the
primary analysis.

## Private/shared equivalence controls

PASS:

- legacy private/shared semantics are tested directly;
- probabilistic `p=0` and `p=1` reproduce shared/private recipient counts;
- feedback randomness is on a separate RNG and cannot alter task or router RNG;
- the matched replication YAMLs are identical after removing only
  `condition.memory_mode` and source provenance.

## Batch design

Files:

- `configs/research/replication_private.yaml`
- `configs/research/replication_shared.yaml`
- `configs/research/batches/private_shared_replication_5seeds.yaml`

The batch contains seeds `[1,2,3,4,5]`, both legacy conditions, four agents,
twenty rounds, fixed probes, `[0,10,20]` checkpoints, and technical retries `=1`.
The planner records config hashes, prompt hash, probe hash, effective seeds,
model/backend, expected OMP version, call counts, and retry ceiling.

## Checkpoint choice and rationale

| Schedule | Interaction/run | Probe/run | Nominal/run | Retry ceiling/run | Nominal/10 runs |
|---|---:|---:|---:|---:|---:|
| `[0,20]` | 80 | 320 | 400 | 800 | 4,000 |
| `[0,10,20]` | 80 | 480 | 560 | 1,120 | 5,600 |
| `[0,5,10,15,20]` | 80 | 800 | 880 | 1,760 | 8,800 |

Schedule B is the first replication choice: it adds a midpoint without the
five-checkpoint cost. Cheap online observables remain available at every round.

## Cost estimate

No monetary estimate is currently defensible. Existing OMP artifacts report
partial usage and no provider-reported cost; pricing is not configured in the
YAMLs. The batch is therefore quantified in physical calls only:

- 5 paired seeds = 10 runs;
- 5,600 nominal completions;
- 11,200 theoretical attempts with one retry per logical completion.

After a provider price and complete usage are available, cost should be derived
from recorded usage, not estimated from character counts. At present it cannot
be honestly classified as cents, dollars, or tens of dollars.

## Wall-clock estimate

These are rough estimates using the latest real runs, concurrency `=4`, and
recorded latencies. They are not promises:

| Condition | A `[0,20]` | B `[0,10,20]` | C `[0,5,10,15,20]` |
|---|---:|---:|---:|
| PRIVATE | ~38 min | ~48 min | ~67 min |
| SHARED | ~88 min | ~120 min | ~184 min |

The five-pair B batch is therefore roughly **14 hours** of serial wall time,
with a wide tail risk. It is safer to run one paired seed first and continue
only after inspecting health. The shared estimate is dominated by checkpoint-20
timeouts and stream/chunk failures.

## Runtime risks

Offline evidence from the existing shared run shows:

- 49 timeout errors;
- 2 parser errors;
- 14 other stream/chunk errors;
- 386/400 logical completion coverage.

The errors include OMP separator/chunk-limit failures and 120-second timeouts.
The likely causes are provider/OMP process concurrency, stream framing, or
service queue/rate-limit behavior; the artifacts do not prove a specific 429
rate limit. Shared memory reaches the same `recent_k=8` prompt budget, so no
semantic prompt change was made. This remains a runtime risk and a mandatory
health gate, not a scientific interpretation.

## Health criteria

`emergent_specialization.health` reports expected logical completions, successful
logical completions, attempts, retries, timeout/parse/other errors, completion
coverage, usage coverage, and latency summaries.

- `healthy`: all expected logical completions succeeded, no errors/retries, full
  usage coverage;
- `warning`: complete logical coverage but retries/errors or partial usage;
- `invalid`: one or more logical completions are missing.

The batch resume logic skips only `healthy` matching artifacts. A process that
exits `completed` with missing completions is rerunnable and never silently
treated as valid data.

## Analysis plan

For the ten completed runs:

1. generate cheap online JSONL trajectories for every round;
2. generate per-run reports from raw artifacts;
3. aggregate scalar checkpoint metrics;
4. inspect normalized HSE trajectories with thin per-seed lines and condition
   summaries;
5. report each paired `D_s(t)` value from `aggregate.json`'s
   `paired_delta_hse` field;
6. use utilization, memory inequality, competence, oracle gain, and MI as
   secondary diagnostics;
7. inspect raw-label argmax counts only for exchangeability sanity.

Do not perform significance theater with five seeds and do not call HSE alone
specialization.

## Exact commands

### Plan only

```bash
uv run python -m emergent_specialization.batch \
  --config configs/research/batches/private_shared_replication_5seeds.yaml \
  --plan --json > /tmp/private-shared-replication-plan.json
```

### Run only paired seed 1

This is the recommended first manual execution. It runs PRIVATE then SHARED
sequentially through the secure Bitwarden launcher:

```bash
uv run python -m emergent_specialization.batch \
  --config configs/research/batches/private_shared_replication_5seeds.yaml \
  --run --confirm-real --only-seed 1
```

Equivalent individual commands, if you want to stop between conditions:

```bash
./scripts/run-deepseek-experiment.sh \
  --config configs/research/replication_private.yaml \
  --seed 1 --output-dir data/runs/replication
```

```bash
./scripts/run-deepseek-experiment.sh \
  --config configs/research/replication_shared.yaml \
  --seed 1 --output-dir data/runs/replication
```

### Run all five paired seeds

```bash
uv run python -m emergent_specialization.batch \
  --config configs/research/batches/private_shared_replication_5seeds.yaml \
  --run --confirm-real
```

### Health and aggregate completed artifacts

```bash
for run in data/runs/replication/*; do
  uv run python -m emergent_specialization.health --run "$run" \
    > "reports/replication-health-$(basename "$run").json"
done
```

```bash
uv run python -m emergent_specialization.aggregate \
  data/runs/replication/* \
  --output reports/replication-aggregate.json
```

### Generate online trajectories without modifying raw run directories

```bash
mkdir -p reports/replication-online
for run in data/runs/replication/*; do
  uv run python -m emergent_specialization.metrics.online \
    --run "$run" \
    --output "reports/replication-online/$(basename "$run").jsonl" \
    --mi-permutations 100
done
```

## Things deliberately NOT included

- no intermediate feedback-locality conditions;
- no epsilon, interventions, ablations, replacement, topology, population
  changes, longer horizons, optimization, or model fitting;
- no changes to hidden rules, prompts, router, memory budget, parser, OMP flags,
  or raw results;
- no DeepSeek calls in this preparation session.

## Remaining blockers

There is no semantic blocker to starting one manual paired seed. The practical
blocker is shared-runtime reliability: previous shared artifacts were invalid
under the strict health gate. A human should review the first paired seed's
health before spending the remaining budget. Provider pricing/complete usage is
also unavailable for monetary accounting.
