# Random-routing mechanism control

> **STATUS: PARTIAL / BLOCKED.** Offline descriptive report only. The pre-specified ten-pair control stopped after an incomplete private seed-3 run; no later seeds were started.

## Scope and health gate

This control was designed to separate information locality from confidence-driven selection: the random router is paired across private and shared feedback, with the Gate 1 confidence baseline retained as a separate reference. The official runner completed random seeds 1–2 and stopped at private seed 3 after both attempts for one probe returned `answer: 7`, outside the allowed answer domain `[0, 6]`. The resulting run has 201 missing logical probe completions and is invalid/incomplete; it is not included in endpoint aggregates.

Random control: **4/20 runs complete**, **2/10 pairs complete**, observed cost **US$0.071348**, physical attempts **2610**, retries **10**, parse errors **8**, empty-content errors **3**, timeouts **0**, rate limits **0**. The hard cap was US$1.00 and the physical ceiling was 14,000.

The failed artifact remains in `health_inventory.csv`; it is not silently discarded.

## Pre-specified contrasts

At checkpoint 20: `D_conf_HSE = ΔHSE(confidence/private) − ΔHSE(confidence/shared)`, `D_rand_HSE = ΔHSE(random/private) − ΔHSE(random/shared)`, and `G_HSE = D_conf_HSE − D_rand_HSE`. The Φ contrasts are defined analogously. These are descriptive paired quantities, not inferential estimates.

| contrast | n | mean | median | fraction positive |
|---|---:|---:|---:|---:|
| D_conf_HSE | 10 | +0.2151 | +0.2424 | +0.9000 |
| D_rand_HSE | 2 | +0.3105 | +0.3105 | +1.0000 |
| G_HSE | 2 | -0.2949 | -0.2949 | +0.0000 |
| D_conf_Phi | 10 | +0.0031 | +0.0058 | +0.6000 |
| D_rand_Phi | 2 | +0.0117 | +0.0117 | +1.0000 |
| G_Phi | 2 | -0.0089 | -0.0089 | +0.0000 |

The random contrast has n=2 pairs. It is therefore a plumbing/measurement result, not evidence for a mechanism or effect size. Confidence and random controls also differ in sample size and health history here.

## Pairing and semantics

For random seeds 1–2, private/shared task tuples and selected-agent sequences match exactly. Every private round has one recipient; every shared round has four. Random routing does not consult confidence. Probe evaluation uses a state snapshot and does not update controlled memory.

| seed | task sequence equal | selected sequence equal | private recipient counts | shared recipient counts |
|---:|:---:|:---:|---|---|
| 1 | True | True | [1] | [4] |
| 2 | True | True | [1] | [4] |

## Random-routing MI null

The permutation diagnostic fixes the observed world sequence and shuffles selected-agent labels. It is a finite-sample sanity check, not a p-value.

![Random MI null](figures/random_mi_null.png)

## Figures and tables

- `tables/health_inventory.csv` — all random and Gate 1 health/provenance rows.
- `tables/paired_sequence_audit.csv` — exact task/route and recipient checks.
- `tables/mechanism_contrasts.csv` — per-seed D/G values.
- `tables/checkpoint_metrics.csv` — B(t), Φ(t), utilization, MI, alignment, oracle and matching diagnostics.
- `tables/competence_matrix_long.csv`, `tables/routing_matrix_long.csv`, `tables/online_accuracy.csv`.

![Developmental HSE](figures/delta_hse_all_cells.png)

![Developmental Phi](figures/delta_phi_all_cells.png)

![Mechanism HSE](figures/g_hse_by_seed.png)

![Mechanism Phi](figures/g_phi_by_seed.png)

## Interpretation boundary

The completed random pairs validate the plumbing of a paired random-routing control, but not the ten-pair experiment. A difference between random/private and random/shared cannot be separated from seed variation with two pairs. The invalid seed-3 response is a runtime/model-output validity issue, not a scientific result. No claim of specialization, useful division of labor, or causal mechanism is warranted.

**Gate 2 remains LOCKED.** No long-horizon, softmax, locality sweep, intervention, or other model experiment was started.

## Provenance

- Raw artifacts: `data/runs/campaigns/developmental-dynamics-v1/`.
- Campaign manifest: `data/campaigns/developmental-dynamics-v1/campaign.json`.
- Pre-run tooling HEAD: `c2a7e3e`.
- Probe-set hash: `cb234422389ff7d5a04566112a483f147e4a3d1212b1c69fbb0396ec9ca4c55e`.

Do not launch further inference from this report without human review of the invalid seed-3 run and an explicit decision about whether to resume the pre-specified gate.
