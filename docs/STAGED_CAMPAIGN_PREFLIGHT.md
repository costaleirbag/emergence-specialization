# Staged campaign preflight

## READY: YES

Ready means the human-gated preparation is complete. No real inference was
authorized or executed in this session. Gate 1 itself remains planned and must
be started manually later.

## Branch and HEAD

- Branch: `research/developmental-dynamics`
- Current HEAD: recorded after the final local commit
- Scientific/config base commit: recorded in
  `data/campaigns/developmental-dynamics-v1/campaign.json`
- Existing untracked user files were preserved and not staged.

## Tests and compile

- Full unittest suite: **pass** (including staged lifecycle and spectral tests).
- `uv run python -m compileall -q src`: **pass**.
- All lifecycle execution tests use temporary configs and `--dry-run`/MockBackend.

## Campaign architecture

The manifest is protocol version `staged-v2`. Planning, status, approval and
interim reports are offline. Real execution requires both a gate-specific command
and `--confirm-real`; the default command only prints a plan.

## Gate 1

- Paired seeds: 10 (seeds 1–10).
- New runs: 18 (seeds 2–10, because seed 1 is reused).
- Reused runs: 2, one private and one shared.
- Nominal new completions: 10,080.
- Expected nominal cost: approximately `$0.363148`.
- Hard observed budget: `$1.00`.
- Physical-attempt ceiling: 12,600.
- Status: `planned`.

The reused artifacts are exact config/probe matches and are marked
`HEALTHY / CLEAN` (private) and `HEALTHY / RECOVERED` (shared). They are not
counted as new Gate 1 spend.

## Gate 2

- Target: 50 paired seeds total.
- Incremental tranche: seeds 11–50, 80 runs / 44,800 logical completions.
- Estimated incremental cost: approximately `$1.613992`.
- Status: **LOCKED**.
- Requires explicit human approval referencing the Gate 1 interim report hash.
- No Gate 2 budget is authorized by this session.

## Optional experiments

- Random routing: preserved, optional, not unlocked.
- Long horizon: preserved, optional, not unlocked.
- Softmax/locality/memory/intervention candidates: documentation only.

## Resume and duplicate protection

Stable identities include campaign, protocol version, stage/gate, seed, condition
and config hash. Healthy exact artifacts are reused; incomplete exact artifacts
are resumed in place; raw artifacts are never overwritten. Paired completeness
requires both private and shared conditions.

## Health and cost guards

The runner distinguishes logical completions, physical attempts, usage-bearing
attempts, retries and observed cost. Gate 1 stops at the observed `$1.00` cap or
its finite physical-attempt ceiling. Recovered runs remain usable but flagged;
incomplete pairs block paired interpretation.

## Interim report

The offline command produces:

```text
reports/campaigns/developmental-dynamics-v1/gate-1/INTERIM_REPORT.md
reports/campaigns/developmental-dynamics-v1/gate-1/interim_summary.json
reports/campaigns/developmental-dynamics-v1/gate-1/trajectory_data.json
reports/campaigns/developmental-dynamics-v1/gate-1/paired_terminal.csv
```

The report starts with data quality, followed by per-seed HSE deltas, Phi,
effective competence dimensionality, utilization, MI, routing alignment when
available, complementarity and explicit human-review questions.

## Exact safe commands

```bash
uv run python -m emergent_specialization.campaign --plan-gate gate_1_replication
uv run python -m emergent_specialization.campaign --plan-gate gate_1_replication --max-new-pairs 2
uv run python -m emergent_specialization.campaign --plan-gate gate_1_replication
uv run python -m emergent_specialization.campaign --status
uv run python -m emergent_specialization.campaign --cost
uv run python -m emergent_specialization.campaign --report-gate gate_1_replication
```

Future paid commands (do not run during this preparation session):

```bash
uv run python -m emergent_specialization.campaign \
  --run-gate gate_1_replication --max-new-pairs 2 --confirm-real
uv run python -m emergent_specialization.campaign --resume --confirm-real
```

## Real model call audit

```text
DeepSeek calls: 0
OMP real calls: 0
External LLM calls: 0
Secrets accessed: 0
Bitwarden unlocks: 0
Keychain secret reads: 0
Paid inference calls: 0
```

## Remaining blockers

There is no scientific blocker. The only remaining action is a human decision to
run Gate 1. Gate 2 and all candidate mechanisms remain locked/optional until the
Gate 1 interim report is reviewed by a human.
