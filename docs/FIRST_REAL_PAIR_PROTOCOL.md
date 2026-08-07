# First real paired seed-1 protocol

This document is the decision gate for the first new PRIVATE/SHARED pair. It
describes the existing baseline; it does not change the experiment dynamics.

## Before either run

- Work on `research/developmental-dynamics` at the audited HEAD reported by
  `git rev-parse HEAD`.
- Keep the config files and fixed probe set unchanged between conditions.
- Confirm the plan with `--plan --only-seed 1`.
- Confirm the suite and compile checks are green.
- Record the private/shared config hashes, the probe-set hash, model/backend,
  seed, checkpoint schedule, and retry policy from the plan manifest.
- Do not declare a scientific result from a run whose health gate is invalid.

## Paired design

| Field | Both conditions |
|---|---|
| Seed | 1 |
| Agents | 4 |
| Interaction rounds | 20 |
| Checkpoints | 0, 10, 20 |
| Fixed probes | 40 per checkpoint |
| Model | `deepseek-v4-flash` |
| Backend | Official DeepSeek API through `DeepSeekDirectBackend` |
| Memory | Python-owned `recent_k=8` |
| Router | confidence, `epsilon=0` |
| Retries | `technical_retries=1`, max 2 attempts/logical completion |
| Physical guard | 700 attempts/run |
| Cost guard | USD 0.50/run (usage-based estimate) |

The only intended condition difference is feedback locality:

- **PRIVATE:** the selected agent receives the selected task's experience.
- **SHARED:** every agent receives the same selected experience.

No intervention, probabilistic locality, role assignment, no-memory condition,
topology change, epsilon exploration, or minimal-model tuning is part of this
pair.

## Run order

1. Run PRIVATE seed 1.
2. Run the health command below and inspect the artifacts.
3. Run SHARED seed 1 only if PRIVATE is technically interpretable. The shared
   run is still required even if PRIVATE looks scientifically interesting.
4. Run the paired analysis only after both artifacts have passed the chosen
   health gate.

## Health gate

The first question after each run is infrastructure, not HSE:

- `healthy`: 100% logical completion coverage, no retries/errors, complete
  usage metadata;
- `healthy_recovered`: 100% logical coverage but recovered retries/errors or
  partial usage;
- `invalid`: one or more logical completions are missing, or the run status is
  incomplete/failed.

An invalid condition must not be silently excluded or followed automatically by
seeds 2–5. Preserve the raw directory and report the missing logical calls.
Warnings may be retained only with an explicit methodological note; a clean
replication target is `healthy`.

## Scientific analysis after health

Reconstruct the checkpoint trajectory:

- `B(t)` through behavioral vectors and HSE;
- `A(t)` through the competence matrix;
- `Delta HSE(t)` relative to checkpoint 0;
- competence differentiation `Phi(t)`;
- utilization entropy and effective number of utilized agents;
- task-agent MI with the seeded permutation-null diagnostic;
- oracle gain and optional routing-alignment/matching diagnostics.

These are distinct observables. Behavioral diversity is not automatically
specialization, and routing concentration is not automatically useful labor.
The private/shared contrast is the causal control for information locality; it
is not an assumption that private feedback is better.

## Exact future commands

All commands in this section are intentionally **not executed by Codex during
the preparation session**.

Plan only the paired seed:

```bash
uv run python -m emergent_specialization.batch \
  --config configs/research/batches/private_shared_replication_5seeds.yaml \
  --plan --only-seed 1 --json
```

The direct backend reads `emergence-specialization.deepseek` / `api` from the
macOS Keychain. Register it once with:

```bash
uv run python -m emergent_specialization.credentials store
uv run python -m emergent_specialization.credentials status
```

Run PRIVATE seed 1 manually:

```bash
uv run python -m emergent_specialization.experiment \
  --config configs/research/replication_private.yaml \
  --seed 1 \
  --output-dir data/runs/replication \
  --confirm-real
```

Run SHARED seed 1 manually, only after the PRIVATE health check:

```bash
uv run python -m emergent_specialization.experiment \
  --config configs/research/replication_shared.yaml \
  --seed 1 \
  --output-dir data/runs/replication \
  --confirm-real
```

If a direct run is interrupted, resume the same directory (never start a new
run or repeat completed logical completions):

```bash
uv run python -m emergent_specialization.experiment \
  --resume data/runs/replication/<run-id> \
  --confirm-real
```

Health after each run:

```bash
uv run python -m emergent_specialization.health --run data/runs/replication/<run-id>
```

Offline online trajectory and MI diagnostic:

```bash
uv run python -m emergent_specialization.metrics.online \
  --run data/runs/replication/<run-id> \
  --output reports/replication-online/<run-id>.jsonl \
  --mi-permutations 100
```

Paired aggregate after both runs:

```bash
uv run python -m emergent_specialization.aggregate \
  data/runs/replication/private-seed1-* \
  data/runs/replication/shared-seed1-* \
  --output reports/replication-seed1-aggregate.json
```

The aggregate command is analysis-only. It never performs inference.

## Minimal-model boundary

The minimal model is a theoretical sandbox for deterministic API and sanity
checks. It is not evidence that the model explains a DeepSeek trajectory.
