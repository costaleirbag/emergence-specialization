# First paired replication readiness report

> **Superseded infrastructure note (2026-08-07):** this historical readiness
> snapshot describes the earlier OMP-backed plan. New replication configs now
> use `DeepSeekDirectBackend`; see
> [DEEPSEEK_DIRECT_MIGRATION_REPORT.md](DEEPSEEK_DIRECT_MIGRATION_REPORT.md) and
> [FIRST_REAL_PAIR_PROTOCOL.md](FIRST_REAL_PAIR_PROTOCOL.md) for the active
> commands. The old OMP observations remain exploratory and unchanged.

## Executive summary

**FIRST REAL PAIRED SEED READY: YES — with a mandatory health gate.**

The new seed-1 PRIVATE/SHARED pair is prepared but has not been executed. The
baseline semantics are covered by tests and a small deterministic MockBackend
pair. The old real seed-1 artifacts remain exploratory and fail the strict
health gate; they are not being silently promoted to replication evidence.

No real model call, OMP inference, external LLM call, Bitwarden unlock, API-key
access, or paid inference was performed in this preparation session.

## Branch and HEAD

- Branch: `research/developmental-dynamics`
- Audited starting HEAD: `ec9c6bf4b7da897ca9fd9393b9887451f2e4ac6c`
- Final implementation tip: verify with `git rev-parse HEAD` after the report
  commit.
- `main` was not modified, merged, rebased, or pushed.
- Working tree before these changes contained one user-owned untracked file:
  `Emergent Specialization Presentation.md`; it was preserved and not staged.

## Test suite

Offline validation performed with MockBackend/toy data:

```text
uv run python -m unittest discover -s tests -v
85 tests: OK
uv run python -m compileall -q src
OK
```

The focused new tests cover `Phi`, routing alignment, matching, incomplete-run
health accounting, analysis fields, and a paired mock end-to-end run.

## Baseline semantic audit

The intended baseline remains unchanged:

- four host-side agents are exchangeable: same model, system prompt, tools,
  decoding intent, and empty memory; no role/persona is derived from an agent
  label;
- the hidden modular rules remain Python/environment-only;
- each interaction samples one task and sends it to every agent;
- confidence routing uses `epsilon=0` and a separate seeded router RNG;
- private feedback updates exactly the selected agent;
- shared feedback copies the selected experience to every agent;
- `recent_k=8` bounds model-visible memory context;
- checkpoint probes use frozen memory snapshots and never call `observe`;
- OMP remains a fresh `--mode rpc --no-session` provider boundary per
  completion;
- no intervention is declared in either replication YAML.

The changes in this preparation are analysis-only or test/documentation
changes. `Phi`, routing alignment, and division-of-labor matching are computed
from checkpoint summaries and cannot affect task generation or routing.

## Exchangeability audit

PASS for code-level checks:

1. response order is canonicalized by agent ID before routing;
2. reversing asynchronous response iteration does not change a tie winner when
   the same seeded RNG is used;
3. ties are chosen with the explicit router RNG, not first-index preference;
4. prompts contain no agent ID, and memory records contain no agent identity;
5. the deterministic MockBackend fallback is agent-label independent;
6. parsing chooses a deterministic last valid response object, not a response
   based on completion order.

This is a harness-level exchangeability audit, not a proof that a remote
provider has no process-order effect. Raw-label occupancy remains a diagnostic;
permutation-invariant summaries are primary.

## Paired RNG/task audit

The task RNG is independent from router and feedback RNGs. With the same seed
and matched config, private and shared mock runs produced identical logged task
sequences. The future pair uses the same seed, model, prompt, fixed probe set,
rounds, checkpoints, router, memory budget, and retry policy.

The effective seed convention for the planned batch is:

```text
task seed     = seed
router seed   = seed + 1
feedback seed = seed + 2
```

## Probe immutability audit

`ExperimentRunner._evaluate_checkpoint` snapshots every agent memory before
launching probe jobs, passes those snapshots to `prompt_parts`, and asserts that
no agent memory changed afterward. The mock suite checks checkpoint memory
counts and the fixed probe set is hash-verified on load.

## Mock end-to-end result

The local script `scripts/generate_mock_readiness.py` executed a tiny private /
shared pair with two agents, three rounds, checkpoints `[0, 2, 3]`, two probes
per world, and `MockBackend` only. It verified:

- metadata, events, metrics, and summary artifacts are produced;
- the paired task sequence is equal across conditions;
- private feedback has one recipient per interaction;
- shared feedback has all agents as recipients;
- checkpoint artifacts contain probe hashes and memory counts;
- health and analysis can consume the resulting artifacts.

The generated figures live under the ignored directory
`reports/mock-readiness/` and are explicitly watermarked:

```text
MOCK / SYNTHETIC — NOT SCIENTIFIC DATA
```

They include normalized HSE, Delta HSE, `Phi(t)`, utilization, competence and
routing heatmaps, and routing entropy versus MI. They are plumbing checks only.

## B(t) readiness

The existing metrics JSONL already reconstructs checkpoint behavioral matrices,
pairwise behavioral distance, HSE, routing, and complementarity. The analysis
layer now exposes checkpoint rows for:

- raw and normalized HSE;
- `Delta HSE` through `hse_trajectory_rows`;
- `Phi(t)` competence differentiation;
- routing alignment `eta_route`;
- one-to-one matching potential and `Delta_match` when `N=K`;
- utilization entropy, task-agent MI, accuracy, and oracle gain.

`Phi(t)` is the population-variance quantity

```text
Phi(t) = (1/K) sum_c Var_i[A_ic(t)]
```

and must not be described as proof of specialization.

## A(t) readiness

`analysis.competence_rows` reconstructs the logged competence matrix
`A_ic(t)` by agent, world, and checkpoint. It is suitable for future heatmaps
and label-aligned multi-seed summaries. Agent labels are not treated as stable
roles without an explicit alignment step.

## Metrics readiness

The primary and diagnostic pipeline is ready offline:

- HSE / normalized HSE;
- baseline-relative Delta HSE;
- utilization entropy and effective utilized-agent count;
- task-agent MI and seeded permutation-null diagnostic;
- best-individual accuracy, oracle accuracy, and oracle gain;
- competence matrices;
- `Phi(t)` competence differentiation;
- routing alignment against random and domain-oracle baselines;
- dependency-free one-to-one matching when the number of agents equals worlds.

Routing alignment and matching are analysis-only. They never feed back into the
router.

## Health gate

`emergent_specialization.health` reports expected logical completions, successful
logical completions, physical attempts, retries, timeout/parse/other errors,
completion coverage, usage coverage, and latency summaries. It now also audits
failed/incomplete directories without checkpoint metrics, so interruption is
classified as `invalid` rather than hidden behind a loader error.

Interpretation:

```text
CLEAN / healthy
    100% logical coverage, no retries/errors, complete usage metadata

WARNING / complete with retries
    100% logical coverage, but recovered retries/errors or partial usage

INVALID / incomplete
    missing logical completions or non-completed run status
```

The batch runner skips only matching `healthy` artifacts. A completed process
with missing calls is not silently treated as valid.

## Old pilot health (offline, exploratory only)

Artifacts audited without modification:

| Run | Expected | Successful | Physical | Retries | Timeouts | Parse | Other | Coverage | Health |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| PRIVATE `private-seed1-20260806T231032Z-ff928a0b` | 400 | 398 | 412 | 12 | 13 | 0 | 1 | 99.5% | invalid |
| SHARED `shared-seed1-20260807T002355Z-557768c8` | 400 | 386 | 451 | 51 | 49 | 2 | 14 | 96.5% | invalid |

Both runs share probe hash
`cb234422389ff7d5a04566112a483f147e4a3d1212b1c69fbb0396ec9ca4c55e` but are
not clean replication evidence. Their recorded endpoint normalized HSE values
were approximately PRIVATE `0.5286 -> 0.7565` and SHARED `0.4410 -> 0.3589`.
Those values are descriptive diagnostics only because the health gate failed.

## Shared runtime risk

Offline evidence from the old artifacts:

| Suspected issue | Evidence | Confidence | Semantic risk of mitigation |
|---|---|---|---|
| OMP/provider queue or process overhead | shared mean inference latency ~42.7s vs private ~15.5s; many attempts approach 120s | medium | lowering concurrency or changing scheduling can alter runtime, not scientific prompts, but must be declared |
| stream framing/chunk limits | 12 `chunk is longer than limit` and 2 `chunk exceed the limit` errors in shared | high for observed failure mode | changing OMP flags/parser may change provider behavior; do not silently patch during the pair |
| request payload growth | serialized controlled memory remains bounded at max 8 items and ~932 chars in both old runs | high evidence against unbounded memory | none if only measured; do not change `recent_k` |
| rate limiting | no explicit HTTP 429 or provider rate-limit marker in the logs | low/undetermined | retry/backoff policy changes call count and wall time; require separate infra study |
| parser fragility | 2 shared parse errors in old run; parser regression tests now cover prose/braces/multiple objects | high for old parser class | fixed in a dedicated prior commit; still report any new parse error |

The correct first response is measurement and the health gate, not a silent
timeout/concurrency change. The new pair keeps the baseline configuration
fixed so runtime failures remain visible.

## Planned real experiment

Files:

- `configs/research/replication_private.yaml`
- `configs/research/replication_shared.yaml`
- `configs/research/batches/private_shared_replication_5seeds.yaml`

The seed-1 plan has exactly two runs:

```text
4 agents × 20 rounds = 80 interaction completions
3 checkpoints × 40 probes × 4 agents = 480 probe completions
nominal total = 560 logical completions per condition
paired nominal total = 1,120 logical completions
technical retry ceiling = 1,120 physical attempts per condition
paired retry ceiling = 2,240 physical attempts
```

The full future five-seed batch is ten runs, 5,600 nominal completions and a
theoretical 11,200 physical-attempt ceiling. These are call counts, not a
monetary estimate; current OMP artifacts do not provide a complete configured
price/cost basis.

Reproducibility values:

| Item | Value |
|---|---|
| Private config SHA-256 | `ca8e07c1426f6da0831d86818e4de904860d6826c4844039097eaa8c61e89df7` |
| Shared config SHA-256 | `56a0e3a59212b79a0407e81d8b7560ce2a6d1bcab844176357aa81f0d53a0d98` |
| System-prompt hash | `3e13fe594467243265296f8ad2d25a57e5d99f3586a8b34a901bf06552104e72` |
| Probe-set hash | `cb234422389ff7d5a04566112a483f147e4a3d1212b1c69fbb0396ec9ca4c55e` |
| Model | `deepseek/deepseek-v4-flash` |
| Backend | OMP via `scripts/run-deepseek-experiment.sh` |
| OMP observed during planning | `omp/17.2.10` |
| Seed | 1 |
| Checkpoints | `[0, 10, 20]` |

## Exact future commands

The real commands below are **DO NOT RUN DURING THIS CODEX SESSION**.

### A. Full test suite

```bash
uv run python -m unittest discover -s tests -v
```

### B. Full batch plan (safe)

```bash
uv run python -m emergent_specialization.batch \
  --config configs/research/batches/private_shared_replication_5seeds.yaml \
  --plan --json > /tmp/private-shared-replication-plan.json
```

### C. Plan only seed 1 (safe)

```bash
uv run python -m emergent_specialization.batch \
  --config configs/research/batches/private_shared_replication_5seeds.yaml \
  --plan --only-seed 1 --json
```

### D. Future PRIVATE seed 1 — real, do not run here

```bash
./scripts/run-deepseek-experiment.sh \
  --config configs/research/replication_private.yaml \
  --seed 1 \
  --output-dir data/runs/replication
```

### E. Future SHARED seed 1 — real, only after PRIVATE health, do not run here

```bash
./scripts/run-deepseek-experiment.sh \
  --config configs/research/replication_shared.yaml \
  --seed 1 \
  --output-dir data/runs/replication
```

### F. Health after each run (analysis-only)

```bash
uv run python -m emergent_specialization.health --run data/runs/replication/<run-id>
```

### G. Aggregate paired seed 1 (analysis-only)

```bash
uv run python -m emergent_specialization.aggregate \
  data/runs/replication/private-seed1-* \
  data/runs/replication/shared-seed1-* \
  --output reports/replication-seed1-aggregate.json
```

### H. Online trajectory and MI diagnostic (analysis-only)

```bash
uv run python -m emergent_specialization.metrics.online \
  --run data/runs/replication/<run-id> \
  --output reports/replication-online/<run-id>.jsonl \
  --mi-permutations 100
```

For a rendered notebook/HTML report after both runs:

```bash
uv run --group report emergence-compare \
  --runs data/runs/replication/private-seed1-<id> data/runs/replication/shared-seed1-<id> \
  --output reports/replication-seed1-report
```

### I. Future seeds 2–5 — only after the seed-1 pair passes the gate

```bash
uv run python -m emergent_specialization.batch \
  --config configs/research/batches/private_shared_replication_5seeds.yaml \
  --run --confirm-real
```

## Real model call audit

```text
DeepSeek calls: 0
OMP real inference calls: 0
external LLM calls: 0
secrets accessed: 0
Bitwarden unlocks: 0
paid inference calls: 0
```

The planner performed only local config/hash work and a version check. The mock
figure generator used the deterministic in-process MockBackend. No launcher was
invoked.

## Remaining blockers

1. The new real pair still needs to be run manually through the secure launcher.
2. The old shared OMP reliability problem is unresolved and may produce an
   invalid new run; do not reinterpret it as a scientific effect.
3. Monetary cost remains unavailable until complete provider usage and a
   declared price basis are present.
4. A clean pair is a prerequisite for seeds 2–5; no automatic continuation is
   enabled by this preparation.

## Scientific cautions

- HSE measures behavioral diversity, not specialization.
- `Phi` measures competence differentiation, not useful labor.
- high routing concentration can be collapse;
- MI measures organization, not competence;
- oracle gain measures complementarity potential, not causal specialization;
- the private/shared comparison is the information-locality control;
- one seed is a feasibility/replication check, not a population-level claim;
- the minimal model remains a theoretical sandbox, never an explanation of the
  LLM result.
