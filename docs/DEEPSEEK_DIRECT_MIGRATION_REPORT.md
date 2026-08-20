# DeepSeek Direct migration report

## Executive summary

The new replication path is prepared to use the official DeepSeek API directly
through a long-lived OpenAI-compatible client. OMP remains available for
historical artifacts and legacy smoke/pilot reproduction, but is no longer the
primary backend for `configs/research/replication_*.yaml`.

**DEEPSEEK DIRECT MIGRATION READY: YES.** The implementation and test phase
made no model calls; after that gate, the explicitly authorized one-call doctor
was executed successfully (recorded below). No scientific experiment was run.

Starting audited HEAD: `a481b4bc0fae286bf14671193dd6e5f8727abb4d`  
Branch: `research/developmental-dynamics`  
Final HEAD: see `git rev-parse HEAD` at handoff; the exact final commit is
reported in the terminal summary below (the report is included in the final
documentation commit).

## Why this changes the infrastructure, not the science

The controlled state remains Python-owned: hidden worlds, task generation and
RNG streams, identical prompts, confidence routing, feedback locality,
`recent_k=8`, checkpoint snapshots, probe set, metrics, and private/shared
semantics are unchanged. The provider now receives the same complete stateless
request directly instead of passing it through an OMP process and stream
framing layer. Historical OMP runs remain explicitly labeled by their backend.

## Implementation

- `DeepSeekDirectBackend` uses one `AsyncOpenAI` client per run with HTTPX
  connection pooling and SDK `max_retries=0`.
- Requests use `deepseek-v4-flash`, `stream=False`, JSON Output, and
  `extra_body={"thinking": {"type": "disabled"}, "user_id":
  "emergence-specialization"}`. No tools, sessions, or server-side memory are
  used.
- The prompt already contains the required JSON keyword and example. Parsing
  remains defensive and validates the experimental schema (`answer` integer
  0–6 and `confidence` 0–1).
- The model does not expose a documented sampling-seed control for this
  configuration; metadata records `provider_sampling_seed_control: unavailable`.
- `credential_source: keychain` is the default. `keyring` is required to use a
  safe macOS Keychain backend; no `.env`, shell variable, YAML secret, or CLI
  key is used. Explicit `credential_source: env` exists for controlled CI use
  only and never falls back silently.

## Reproducibility and cost

The matched configs are identical except `condition.memory_mode` (`private` vs
`shared`). They use seed 1, four agents, 20 rounds, checkpoints `[0, 10, 20]`,
and 40 fixed probes/checkpoint. The probe hash is recorded in each run manifest.

Nominal work per condition is:

```
20 * 4 interaction completions = 80
3 * 40 * 4 probe completions    = 480
nominal logical completions     = 560
```

Runtime guards are declarative: at most 700 physical attempts, at most USD
0.50 observed usage-based cost, and at most two attempts per logical
completion. The physical-attempt guard is independent because a provider-side
timeout may be billable even when usage is not returned. Pricing snapshots in
the configs are USD 0.14/M uncached input, USD 0.0028/M cached input, and USD
0.28/M output; reconfirm before later studies.

## Retry and timeout policy

The direct adapter classifies 400/401/402/422 as fail-fast (format,
authentication, balance, and parameter errors). 429, 500, 503, transient
transport failures, and empty response content are retryable. The runtime owns
bounded exponential backoff with deterministic jitter and honors `Retry-After`.
The SDK itself performs no retries.

Timeouts are separate and configurable: connect 10 seconds, read/inactivity
600 seconds, absolute request 660 seconds, and pool acquisition 10 seconds.
These values are infrastructure choices, not changes to scientific dynamics.

## Resumability and atomicity

Every physical attempt is stored in `events.jsonl` and the local
`run_state.sqlite3` journal. Logical IDs include run/config/condition/seed,
phase, round or checkpoint, task, agent, prompt hash, and controlled-memory
hash, but not physical attempt number. A successful logical completion is
reused on resume.

Interaction rounds are atomic at the scientific boundary: partial candidates
are logged, but routing and feedback do not run until all four candidates are
available. A committed round records candidates, tie decision, selected agent,
correctness, recipients, and state transitions. Checkpoints persist a frozen
memory snapshot hash before launching independent probes; a mismatch fails
hard. Probe workers never call `observe`.

`--resume` reads the immutable original manifest, prints expected/complete/
missing work, prior attempts and observed cost, and requires `--confirm-real`
only when incomplete direct work remains. A complete run resumes with zero API
calls. Ctrl+C and SIGTERM mark the run interrupted, flush the journal/summary,
and print the exact resume command.

## Concurrency and benchmark

Interaction concurrency is 4 and rounds remain sequential. The benchmark froze
probe concurrency at 32 in both replication configs, with a pooled client sized
for that workload. The benchmark is
separate from scientific data and writes only to
`reports/infrastructure-benchmarks/`; it tests 4, 8, 16, and 32 concurrency
with 32 small probe-like requests/level. It is plan-only unless
`--confirm-real` is supplied. The recommendation is conservative: highest
tested level with zero failures and zero 429s, followed by p95 inspection; it
does not modify scientific configs.

## Health and accounting

`emergent_specialization.health` groups attempts by logical completion and
reports logical coverage, physical attempts, retry/error categories, latency,
usage coverage, and observed cost. The classifications are:

- **HEALTHY / CLEAN** — complete logical coverage, no retries/errors, complete
  usage;
- **HEALTHY / RECOVERED** — complete logical coverage with recovered transient
  failures/retries or partial usage;
- **INVALID / INCOMPLETE** — missing logical completions or incomplete run
  state.

Recovered failures are never silently discarded. Old OMP exploratory pilots
remain offline historical artifacts and are not replication evidence.

## Files and dependencies

Added or changed in this migration:

- `src/emergent_specialization/providers/deepseek_direct.py`
- `src/emergent_specialization/credentials.py`
- `src/emergent_specialization/journal.py`
- `src/emergent_specialization/retry.py`
- `src/emergent_specialization/deepseek_doctor.py`
- `src/emergent_specialization/benchmark/`
- runtime/config/model/logging/cost/health/batch changes
- direct replication YAMLs and protocol/README updates
- direct provider, credential, resume, budget, and mock tests

New runtime dependencies are `openai`, `httpx`, and `keyring`. No agent
framework or new scientific dependency was added.

## Cache audit

The existing prompt serialization preserves a stable system prompt followed by
controlled memory and then the variable task. This is an opportunity for
provider prefix caching; the migration does not reorder prompts or claim cache
hits in advance. Raw and normalized usage records expose cache fields when the
provider returns them.

## Exact human commands

These commands are not executed by Codex in this migration session.

```bash
# A. Store and inspect the Keychain credential (hidden input; no key is printed)
uv run python -m emergent_specialization.credentials store
uv run python -m emergent_specialization.credentials status

# B. Offline doctor (zero model calls)
uv run python -m emergent_specialization.deepseek_doctor

# C. Optional one-call doctor — DO NOT RUN DURING THIS CODEX SESSION
uv run python -m emergent_specialization.deepseek_doctor --confirm-real

# D. Optional real benchmark — DO NOT RUN DURING THIS CODEX SESSION
uv run python -m emergent_specialization.benchmark.deepseek \
  --concurrency 4,8,16,32 --jobs-per-level 32 \
  --max-cost-usd 0.25 --confirm-real

# E. Plan paired seed 1 (zero model calls)
uv run python -m emergent_specialization.batch \
  --config configs/research/batches/private_shared_replication_5seeds.yaml \
  --plan --only-seed 1 --json

# F. PRIVATE seed 1 — DO NOT RUN DURING THIS CODEX SESSION
uv run python -m emergent_specialization.experiment \
  --config configs/research/replication_private.yaml --seed 1 \
  --output-dir data/runs/replication --confirm-real

# G. Health after PRIVATE
uv run python -m emergent_specialization.health --run data/runs/replication/<run-id>

# H. Resume an interrupted direct run — DO NOT RUN DURING THIS CODEX SESSION
uv run python -m emergent_specialization.experiment \
  --resume data/runs/replication/<run-id> --confirm-real

# I. SHARED seed 1, only after PRIVATE health — DO NOT RUN DURING THIS CODEX SESSION
uv run python -m emergent_specialization.experiment \
  --config configs/research/replication_shared.yaml --seed 1 \
  --output-dir data/runs/replication --confirm-real

# J. Health after SHARED
uv run python -m emergent_specialization.health --run data/runs/replication/<run-id>

# K. Offline paired aggregate/report (after both runs)
uv run python -m emergent_specialization.aggregate \
  data/runs/replication/private-seed1-* \
  data/runs/replication/shared-seed1-* \
  --output reports/replication-seed1-aggregate.json

# L. Remove the credential later (prompts for DELETE)
uv run python -m emergent_specialization.credentials delete
```

## Validation performed in this session

- Unit suite: 95 tests passed; no tests use the network or a real credential.
- `compileall -q src tests`: passed.
- Offline doctor and benchmark plan: passed; reported zero model calls.
- Batch planner for seed 1: 2 planned runs, 560 logical completions/run, 700
  physical-attempt ceiling.
- OMP, Bitwarden, and paid scientific inference calls: **0**.
- Keychain credential reads: **1**, only for the authorized doctor completion;
  the key value was never printed or persisted.

## Authorized infrastructure benchmark result

The authorized benchmark ran 128/128 probe-like requests (32 at each tested
concurrency) with zero retries, zero HTTP 429, zero 5xx, and zero timeouts.
Throughput was 3.633, 7.607, 15.332, and 23.097 requests/s at concurrency 4,
8, 16, and 32; p95 latency was 1.236, 1.183, 1.018, and 1.333 seconds. The
observed total cost was USD 0.00163072. No latency knee was observed by 32, so
`probe_concurrency: 32` was applied identically to both replication configs.
Cache hit ratio was 0.0 in this deliberately namespace-separated benchmark;
that is an infrastructure observation, not a scientific conclusion.

## Authorized one-call doctor result

After the offline validation, one explicitly authorized doctor completion was
run with `--confirm-real`. It used the Keychain credential, returned the exact
configured model `deepseek-v4-flash`, parsed successfully, and produced no
retry/error. Latency was 3.282 seconds; usage was 59 input tokens (0 cache-hit,
59 cache-miss), 14 output tokens, 73 total. The artifact is
`reports/infrastructure-doctor/doctor.json` and is marked **NOT SCIENTIFIC
DATA**. This was the only real model call in the session.

Before the first real pair, the human should run the offline doctor, optionally
the one-call doctor/benchmark, then freeze this commit and the runtime settings.
Do not interpret the first direct pair causally until both conditions pass the
health gate; do not change configs between them.
