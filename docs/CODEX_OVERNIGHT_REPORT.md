# Codex overnight report

## Scope and safety

- Branch: `research/developmental-dynamics`
- Initial implementation HEAD: `ffb2012`
- Final implementation HEAD before this report commit: `5d9d8d1`
- No DeepSeek/OMP inference was executed.
- Bitwarden was never unlocked and no credential was accessed.
- Existing raw runs under `data/runs/` were read-only inputs; no raw run files
  were changed.
- No push, rebase, force-push, or remote change was performed.

## Commits created

1. `902d9c5` — Add temporal trajectory and batch analysis infrastructure
2. `c3d0ae2` — Add interventions and future research scaffolding
3. `5bc9b1c` — Test scheduled feedback locality config
4. `5d9d8d1` — Clean permutation metric imports

The report itself is the next local commit. Verify the exact tip with:

```bash
git rev-parse HEAD
git log --oneline --decorate -8
```

## Main files and features

### Complete and tested

- Checkpoints accept the existing explicit list and `checkpoints: {every: N}`;
  schedules include 0 and the final round, while `[]` remains valid.
- Cheap, probe-free online trajectory extraction in
  `metrics/online.py`, including routing, accuracy, confidence, memory,
  concentration, switching, and cumulative MI observables.
- Dependency-free batch planning in `batch.py`; default is plan-only and prints
  nominal and retry-ceiling call counts.
- Offline aggregation of completed runs in `aggregate.py`, including scalar
  checkpoint summaries and paired condition differences.
- Permutation-aware competence alignment and ensemble symmetry/within-run
  asymmetry diagnostics in `metrics/permutation.py`.
- Seeded MI permutation/null diagnostic and HSE delta helpers.
- Feedback locality abstraction with private/shared compatibility,
  probabilistic `private_probability`, and an explicit round schedule. The
  endpoints `p=0` and `p=1` are covered by tests.
- Python-owned memory interventions: swap, erase, clone, and world-filtered
  transplant. Interventions are logged with before/after counts and hashes.
- Initial memory conditions for micro-perturbation studies.
- Fixed-N-safe `PopulationState` scaffold for ablation, naive replacement, and
  reintroduction. The fixed-N experiment runner intentionally rejects dynamic
  population operations until its matrix schemas are generalized.
- Transparent recovery helpers for performance, niche, and routing replacement
  time.
- Independent deterministic minimal non-LLM model under
  `src/emergent_specialization/minimal_model/`.
- Research configs and concise protocol/agenda/intervention/minimal-model docs.

### Partial / deliberately deferred

- Online observables are currently derived offline from `events.jsonl`; no
  scheduler or early-termination controller exists.
- Population changes are a tested state scaffold, not integrated into the
  fixed-N runner or fixed-size checkpoint metrics.
- Role alignment is explicit and small-N; no automatic scientific definition
  of “role” is imposed.
- Hysteresis support covers feedback-locality schedules only. No general
  intervention controller, topology, Bayesian optimization, surrogate model,
  distributed execution, or dashboard was added.
- No claim is made about phase transitions, novelty, causal results, or
  scientific significance.

## Compatibility decisions

The legacy `configs/pilot_private.yaml` and `configs/pilot_shared.yaml` retain
their schema and behavior. `RunConfig.effective_feedback` translates the old
`condition.memory_mode` field; new research configs can opt into the separate
`feedback` section. Probes still use frozen memory snapshots and never mutate
agent memory. OMP session flags, model selection, prompts, router, hidden rules,
and baseline metrics were not changed.

## Validation

The baseline suite had 50 passing tests before this work. The final suite has 70
passing tests:

```bash
uv run python -m unittest discover -s tests -v
```

Offline validation also included bytecode compilation, a deterministic minimal
model demo, online extraction from the completed private run, aggregate analysis
of the existing private/shared pair, and a 10-run batch plan. These demos wrote
only to a temporary directory under `/tmp`.

## Inspect tomorrow

```bash
git status --short
git log --oneline --decorate -8
uv run python -m unittest discover -s tests -v

# No model calls: derive online trajectory to a temporary path
uv run python -m emergent_specialization.metrics.online \
  --run data/runs/<run-id> \
  --output /tmp/<run-id>-online.jsonl

# No model calls: plan the five-seed private/shared batch
uv run python -m emergent_specialization.batch \
  --config configs/research/batches/private_shared_seeds.yaml --plan

# No model calls: aggregate completed runs
uv run python -m emergent_specialization.aggregate \
  data/runs/<private-run> data/runs/<shared-run> \
  --output /tmp/aggregate.json

# No model calls: toy mechanism demo
uv run python - <<'PY'
from emergent_specialization.minimal_model import MinimalModelConfig, simulate
print(simulate(MinimalModelConfig(rounds=40, seed=1)).final_skills)
PY
```

## Research configs

Examples are in `configs/research/`, including trajectory schedules,
probabilistic locality, a locality schedule, memory swap/erase, population
scaffolds, and a one-experience micro-perturbation. They are examples, not an
instruction to spend provider budget. The existing real private/shared pilots
remain the only completed DeepSeek runs known to this session.

## Experiments that are ready versus not ready

Ready for a deliberate future local/mock validation:

- checkpoint schedules;
- online trajectory derivation;
- batch planning;
- aggregate analysis;
- permutation alignment and MI null diagnostics;
- probabilistic/scheduled feedback in the fixed-N runner;
- memory interventions and initial conditions;
- minimal-model mechanism checks.

Not ready for an unattended real sweep:

- dynamic population ablation/replacement with fixed-size probe metrics;
- early stopping or compute allocation;
- topology/communication interventions;
- closed-loop control;
- multi-seed DeepSeek execution without a separate budget and protocol review.

## DO NOT INTERPRET AS RESULTS

This session produced engineering infrastructure only. It produced **zero new
scientific model runs and zero new scientific results**. Existing private/shared
artifacts were inspected for compatibility and used for offline smoke checks;
their previously recorded metrics were not reinterpreted here. Any future
claims about emergence, specialization, causality, resilience, or regime
changes require pre-registered comparisons, repeated seeds, uncertainty
analysis, and independent terminal objectives.

