# Staged campaign protocol

## Scientific rationale

The campaign studies `B -> B(t)`: whether initially exchangeable LLM agents
develop behavioral or competence differentiation under private versus shared
feedback. Behavioral diversity is not automatically specialization, useful
division of labor, or efficient coordination.

The previous 318-run plan was scientifically pre-registered but committed too
much budget before learning whether the first trajectories were informative. The
new protocol therefore acquires evidence in small, human-reviewed tranches:

```text
Gate 1: small paired replication
       -> offline interim report
       -> human decision
Gate 2: larger replication, only if explicitly approved
       -> human decision
Optional candidates: random routing, softmax, locality, memory, horizon,
                     interventions
```

No scientific metric, p-value, or effect size unlocks a later gate.

## Gate 1

- 10 paired seeds, private and shared, confidence router.
- Same frozen direct-DeepSeek baseline: 4 agents, 20 rounds, checkpoints
  `[0, 10, 20]`, 40 probes/checkpoint, `recent_k=8`.
- Existing seed 1 is reused because its config hash, probe hash and health are
  compatible with this protocol.
- New work: seeds 2–10, 18 runs / 9 new pairs / 10,080 logical completions.
- Observed cost forecast: approximately `$0.36315`.
- Hard observed Gate 1 budget: `$1.00`.
- Maximum physical-attempt guard: 12,600 (the per-run configured ceilings
  summed over the 18 new runs).
- Real execution requires an explicit human command with `--confirm-real`.

## Gate 1 outcomes and interim analysis

After Gate 1, `--report-gate gate_1_replication` produces a data-quality-first
report. It records complete pairs, incomplete pairs, CLEAN/RECOVERED/INVALID
runs, logical coverage, attempts, retries, timeout/parse errors, latency and
observed cost before any scientific table.

The report then exposes per-seed `Delta HSE`, `Phi`, effective competence
dimensionality, utilization, MI, oracle gain, competence/routing data and
machine-readable trajectories. It is descriptive and exploratory; it does not
perform significance theater or make an automatic continuation decision.

## Gate 2

Gate 2 expands the baseline to 50 paired seeds total. The incremental tranche is
seeds 11–50 (40 new pairs / 80 runs / 44,800 logical completions), forecast at
approximately `$1.614` using the observed cost rate. It starts **locked** and
has no budget authorization in this session.

An explicit human approval must record the approved budget, timestamp, current
commit and SHA-256 of the Gate 1 interim summary. The approval command only
changes the manifest; it never starts inference. Gate 2 still requires a
separate real-execution command.

## Optional future candidates

The existing random-routing and 100-round configs remain intact, but are
optional candidates rather than automatic Stage B/Stage C steps. Softmax
routing, feedback locality, memory capacity and interventions are likewise
future decisions. Nothing in this manifest unlocks them.

## Resumability and duplicate protection

Each identity is keyed by campaign, protocol version, stage/gate, seed,
condition and immutable config hash. The runner scans metadata and summary
artifacts rather than trusting directory names:

- healthy exact artifacts are reused/skipped;
- incomplete exact artifacts are resumed in place;
- a completed logical completion is never silently rerun;
- raw directories are never overwritten.

Execution is serial within a gate. A pair is complete only when both conditions
are complete; one valid half is not silently used as paired evidence.

## Cost and health guards

The protocol distinguishes logical completions, physical attempts, attempts with
usage (the available billable-attempt proxy), and observed cost. Forecasts are
planning information; the hard Gate 1 guard acts on observed cost and the finite
physical-attempt ceiling. CLEAN, RECOVERED and INVALID health classifications
remain visible in every report.

## Human review questions

Review the individual paired values and trajectories before deciding whether to
approve Gate 2 or choose an optional mechanism experiment. In particular ask
whether private/shared differences are seed-consistent, whether HSE and Phi
agree, whether MI exceeds its null, whether routing exploits competence, whether
oracle gain indicates complementarity, whether labels are symmetric, and whether
the t=20 horizon is still transient.

## Commands

All commands below are safe planning/status/report commands unless explicitly
marked as a future real command.

```bash
# inspect the full staged manifest
uv run python -m emergent_specialization.campaign --plan

# plan Gate 1; plan only the first two pending new pairs
uv run python -m emergent_specialization.campaign \
  --plan-gate gate_1_replication --max-new-pairs 2

# plan all remaining Gate 1 pairs (never executes inference)
uv run python -m emergent_specialization.campaign \
  --plan-gate gate_1_replication

# show state and offline cost
uv run python -m emergent_specialization.campaign --status
uv run python -m emergent_specialization.campaign --cost

# generate the Gate 1 interim report after a human-run tranche
uv run python -m emergent_specialization.campaign \
  --report-gate gate_1_replication

# record explicit human approval after reviewing Gate 1
uv run python -m emergent_specialization.campaign \
  --approve-gate gate_2_replication --budget-usd 2.00

# Gate 2 is plannable only after that approval
uv run python -m emergent_specialization.campaign \
  --plan-gate gate_2_replication
```

The first future paid command is intentionally explicit and must not be run in
the preparation session:

```bash
# DO NOT RUN DURING PREPARATION — first future real tranche
uv run python -m emergent_specialization.campaign \
  --run-gate gate_1_replication --max-new-pairs 2 --confirm-real
```

Subsequent Gate 1 execution uses `--resume --confirm-real`. The current session
does not execute either command.
