# Gate 1 Data Quality

> **GATE 1 — OFFLINE DESCRIPTIVE REPORT.** This document is generated solely from completed immutable run artifacts. It is not a scientific conclusion and does not unlock Gate 2.

## Executive summary

Gate 1 contains **20/20 complete runs** across paired seeds 1–10. Logical coverage is **11200/11200 (100%)**. The set has 3 CLEAN runs and 17 RECOVERED runs; no run is incomplete.

All 20 runs together consumed approximately **US$0.34050** according to recorded per-inference usage. The 18 new runs charged to this Gate 1 execution account for **US$0.30015**; seed 1 was reused and is reported for completeness.

The primary estimand remains the paired developmental contrast, not a maximization target: **D = ΔHSE(private) − ΔHSE(shared)**. HSE, Φ, MI, utilization, alignment, oracle gain and matching are complementary observables; none alone establishes useful specialization.

## Provenance and frozen design

- Campaign: `developmental-dynamics-v1`; Gate 1 status: `complete`; Gate 2 status: `locked`.
- Git commit(s) recorded in run metadata: `973602e1068dfbb4e67fd74c3152def0776500c0, b3462d15ce9ea42cd959cb83708ad5683ede0df5, b7853701d7b171ac75bc7f9791295aff955b9ddf`.
- Backend/model: `deepseek_direct` / `deepseek-v4-flash`; thinking `off`.
- Matched design: 4 agents, 20 rounds, checkpoints `[0, 10, 20]`, 40 probes/checkpoint, `recent_k=8`, confidence router, ε=0.
- Probe-set SHA-256: `cb234422389ff7d5a04566112a483f147e4a3d1212b1c69fbb0396ec9ca4c55e`.
- The paired configs differ in feedback locality only; task/RNG semantics and probe set are shared.
- Raw labels are exchangeable. Ensemble summaries over `agent_0`…`agent_3` are sanity checks, not role claims.

## Health, cost and runtime

- Physical attempts: **11245**; retries: **45**; timeout-class errors: **2**; parse errors: **24**.
- Minimum usage coverage was **0.9965** (one recovered run had partial provider usage metadata). No logical completion is missing.
- One shared seed-6 final checkpoint experienced a long single-probe delay (~610.7 s) but recovered with complete coverage. This is an infrastructure/runtime observation, not a scientific result.

See `tables/data_quality.csv` and `tables/provenance.csv` for the run-level audit.

## Primary HSE trajectories

HSE measures behavioral diversity; ΔHSE is baseline-relative. The plotted ribbons show the min–max range across paired seeds and the faint lines show individual runs. Diversity is not equivalent to specialization or useful division of labor.

![HSE trajectory](figures/hse_trajectory.png)

![Delta HSE](figures/delta_hse_trajectory.png)

At checkpoint 20, the mean paired effect D is **0.2151** across seeds 1–10 and **0.2216** excluding seed 1. These are descriptive summaries; no inferential claim is made here.

![Paired endpoint effect](figures/paired_delta_hse.png)

## Competence differentiation and effective dimensionality

Φ(t) is the population-variance order parameter over the competence matrix. It measures competence differentiation, not specialization. The spectral participation ratio (`d_eff`) summarizes how many independent competence-difference directions are visible; it is not a role count.

![Phi](figures/competence_differentiation_phi.png)

![Effective dimensionality](figures/effective_dimension.png)

## Organization, alignment and complementarity

The following endpoint means are descriptive and retain their separate meanings:

| metric at t=20 | private | shared |
|---|---:|---:|
| normalized HSE | 0.5203 | 0.2715 |
| Φ competence differentiation | 0.0080 | 0.0042 |
| effective dimensionality | 1.7659 | 1.6748 |
| utilization entropy | 0.8428 | 0.9493 |
| task-agent MI | 0.2434 | 0.2515 |
| routing alignment η | -0.0966 | 0.0112 |
| oracle gain | 0.2150 | 0.0850 |
| best individual accuracy | 0.2475 | 0.2225 |
| oracle society accuracy | 0.4625 | 0.3075 |

- Utilization entropy asks whether routing collapsed onto a small subset of agents; high entropy is not proof of specialization.
- Task-agent MI asks whether routing is organized by world/task; it does not establish competence.
- Routing alignment η compares routed competence with random and per-domain-oracle baselines; it can be undefined when the denominator is zero.
- Oracle gain and matching gain address complementarity/potential division of labor; they are not evidence that the actual router exploited the potential.

![Organization and complementarity](figures/organization_and_complementarity.png)

![Routing entropy versus MI](figures/routing_entropy_vs_mi.png)

## Seed 1 sensitivity and raw-label sanity

Seed 1 is the previously completed pair reused by the campaign. Its inclusion changes the endpoint mean D from **0.2216** (seeds 2–10) to **0.2151** (seeds 1–10). This is a sensitivity diagnostic, not a reason to drop the seed.

The raw-label usage plot is included to expose obvious imbalance. Because labels are arbitrary and no role is assigned by ID, any apparent global winner must be checked with permutation-invariant summaries and per-run alignment.

![Raw label usage](figures/label_usage_sanity.png)

![Seed 1 competence matrices](figures/competence_heatmaps_seed1.png)

![Seed 1 routing matrices](figures/routing_heatmaps_seed1.png)

## What the data show (descriptive)

1. The paired design completed technically: all 20 runs contain the expected interaction and probe logical completions.
2. Private and shared trajectories are not identical across seeds; the magnitude and direction of D are seed-dependent rather than a single deterministic path.
3. Shared runs necessarily accumulate feedback in every agent, while private runs accumulate it only in selected agents; this manipulation is visible in `memory_trajectories.csv`.
4. The endpoint observables do not all encode the same construct. In particular, routing concentration, HSE, competence variance, MI and oracle gain can disagree.

## What the data may suggest

- The paired trajectories are suitable for a formal developmental-dynamics analysis of whether information locality changes the distribution of B(t), A(t) and related observables.
- The long probe delay in shared seed 6 suggests that provider/runtime behavior can be a practical confound and should be stratified by latency, retry and fingerprint in later analyses.
- If a future claim concerns functional division of labor, the current data should be read through alignment, complementarity and held-out competence—not HSE alone.

## What the data do not establish

- They do not prove that private feedback is better, that specialization emerged, or that any agent acquired a stable world role.
- They do not identify a phase transition, causal mechanism beyond the pre-registered private/shared manipulation, or generalization outside these synthetic worlds.
- They do not justify optimizing HSE/MI/Φ directly; doing so would invite Goodhart-style pathologies.
- They do not unlock random routing, long-horizon trajectories, Gate 2, or any intervention.

## Human review questions

1. Are paired D and Φ contrasts stable enough across seeds to motivate a pre-registered follow-up?
2. Do condition differences persist after permutation-invariant alignment of agent labels?
3. Does any routing organization align with competence rather than merely concentration?
4. How much of the observed contrast is explained by early accuracy versus collective observables?
5. Is the provider-latency outlier sufficiently independent of condition for a later causal analysis?
6. Would a small, explicitly approved random-routing control add more information than additional baseline seeds?

## Candidate next experiments (advisory only; not executed)

1. **Permutation-invariant paired analysis** of the completed Gate 1 data, including aligned competence/routing matrices and uncertainty intervals.
2. **Early-trajectory predictability** using existing online observables, only after leakage audits and a pre-specified terminal target.
3. **Random-routing control** to separate information locality from confidence-driven selection, if explicitly approved and budgeted.
4. **Long-horizon condition pair** with the same frozen baseline, if the short-horizon contrast and runtime health justify it.

These are ranked by information value, not by the observed scientific result. No new stage is authorized by this report.

## Reproducibility artifacts

- Raw runs: `data/runs/campaigns/developmental-dynamics-v1/`.
- Campaign manifest: `data/campaigns/developmental-dynamics-v1/campaign.json`.
- Machine-readable tables: `tables/`.
- Figures: `figures/`.
- The existing `interim_summary.json` and `trajectory_data.json` remain available; this report adds a richer offline layer without modifying raw runs.

## Gate 2 lock

**Gate 2 remains LOCKED.** A human review is required before any further real inference. This report makes no automatic scientific decision and starts no subsequent stage.
