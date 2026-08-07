# Developmental Dynamics v1 — campaign preflight

Status: **BLOCKED BEFORE REAL CALLS — budget forecast exceeds the hard cap**

This document records the offline preflight for the pre-specified DeepSeek
Direct campaign. No OMP process, model API call, Bitwarden unlock, or secret
read occurred during this preflight.

## Frozen plan

- Provider: `deepseek_direct` (macOS Keychain credential source)
- Model: `deepseek-v4-flash`
- Probe set: 40 fixed probes, SHA-256
  `cb234422389ff7d5a04566112a483f147e4a3d1212b1c69fbb0396ec9ca4c55e`
- Stage A: 100 seeds, confidence routing, 20 rounds, checkpoints `[0, 10, 20]`;
  seed 1 is reused from the existing pair and seeds 2–100 are new.
- Stage B: 50 seeds, random routing, private/shared, 20 rounds, checkpoints
  `[0, 10, 20]`.
- Stage C: seeds 1001–1010, confidence routing, private/shared, 100 rounds,
  checkpoints `[0, 10, ..., 100]`.
- Execution order: one run at a time, Stage A → B → C, private then shared
  within each seed.

## Call accounting

| Stage | Planned runs | New runs | Logical completions/run | New logical completions |
|---|---:|---:|---:|---:|
| A | 200 | 198 | 560 | 110,880 |
| B | 100 | 100 | 560 | 56,000 |
| C | 20 | 20 | 2,160 | 43,200 |
| **Total** | **320** | **318** | — | **210,080** |

The campaign reuses these healthy seed-1 artifacts without rerunning them:

- `data/runs/replication/private-seed1-20260807T215641Z-f4760212`
  (`HEALTHY / CLEAN`)
- `data/runs/replication/shared-seed1-20260807T215816Z-0dec0ddc`
  (`HEALTHY / RECOVERED`)

Their costs are provenance, not new spend in this campaign budget. They were
used only to estimate the cost per logical completion:

- private: `$0.0203192304` for 560 logical completions;
- shared: `$0.0200305784` for 560 logical completions;
- pooled estimate: `$0.000036026615` per logical completion.

Projected new campaign cost:

```text
210,080 × $0.000036026615 = $7.5684712792
hard observed campaign cap = $7.50
```

This is already above the hard cap, before any additional billable timeout or
retry risk. The campaign runner therefore refuses to start a real run and
leaves the manifest in `blocked_budget_forecast` state.

## Offline validation

- Full unittest suite: **101 passed**.
- `compileall -q src`: **passed**.
- Offline DeepSeek doctor: **passed**, zero model calls.
- Keychain credential status: configured; the secret was not read or printed.
- Random routing was added as an explicit analysis-stage ablation. It sorts
  agent IDs before RNG selection, makes no confidence-based choice, uses the
  configured router RNG, and is covered by unit tests. The confidence baseline
  path remains unchanged.
- Campaign plan and manifest are deterministic, resumable, sequential, and
  guarded by both observed-cost and finite physical-attempt limits.

## Decision required before execution

Do not start the campaign under the current `$7.50` cap. To run exactly the
pre-registered campaign, either increase the cap/reserve with an explicit human
decision or reduce the campaign scope in a new pre-registered plan. No scope
was changed automatically.

The safe planning command is:

```bash
uv run python -m emergent_specialization.campaign --plan
```

After a human-approved budget/scope change and a regenerated manifest, the
guarded execution command would be:

```bash
uv run python -m emergent_specialization.campaign --resume --confirm-real
```

That command must remain **not run** until the forecast is below the approved
cap. It uses DeepSeek Direct and the Keychain credential; it does not use OMP or
Bitwarden.
