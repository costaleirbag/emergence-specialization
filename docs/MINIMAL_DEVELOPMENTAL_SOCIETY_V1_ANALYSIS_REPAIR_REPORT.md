# SUPERSEDED ANALYSIS — Minimal Developmental Society V1

> The initial offline competence aggregation contained a niche-accumulator bug.
> The paid raw experiment remains valid, but this report must not be used as the
> canonical scientific analysis. See the corrected repair report and the
> machine-readable outputs under `reports/society/minimal-developmental-society-v1-analysis-repair/`.

# Minimal Developmental Society V1 — analysis repair report

## Executive correction

An accumulator bug in the initial offline competence aggregation produced
impossible accuracies. The raw paid experiment remains valid. The competence
analysis was repaired directly from immutable checkpoint events, with no new
model calls. This report supersedes the original offline conclusions.

## What was wrong

For each agent, the old implementation carried probe accumulators across niches
and divided every cumulative numerator by the single-niche denominator. The fixed
implementation resets accumulators for every `(seed, regime, checkpoint, agent,
niche)` cell and records probe/bit denominators and logical IDs.

## Validation and provenance

- Paid experiment: **VALID**; 47,104 logical completions, DeepSeek Direct
  `deepseek-v4-flash`.
- New model calls/cost: **0 / US$0.00**.
- Raw hashes: `raw_integrity.json`; original invalid outputs:
  `reports/society/minimal-developmental-society-v1/original-analysis-invalid/`.
- Grouped vs pivot aggregation mismatches: **0**.
- Hungarian vs exhaustive matching mismatches: **0**.

## Corrected final competence interaction

| regime | Psi_bit | Psi_joint | Phi_bit | Delta_match_joint |
|---|---:|---:|---:|---:|
| RP | 0.004619 | 0.008764 | 0.005372 | 0.048828 |
| AP4 | 0.005662 | 0.008059 | 0.007111 | 0.041016 |
| AP12 | 0.008787 | 0.016191 | 0.009654 | 0.107422 |
| AS12 | 0.001037 | 0.002737 | 0.001486 | 0.021484 |

## Preregistered H1–H6

- H1 adaptive-private Psi amplification: **PASS**; AP12−RP mean 0.004168, positive seeds 7.
- H2 private-state contrast: **PASS**; AP12−AS12 mean 0.007750, positive seeds 8.
- H3 dynamic Psi AUC: **PASS**; AP12−RP mean 0.002568, positive seeds 8.
- H4 complementarity: **PASS**; AP12−RP matching gain 0.058594.
- H5 competence-aligned organization: **PASS**; AP12 late eta 0.395519.
- H6 realized last-32 team utility: **FAIL**; AP12−RP mean 0.007812.

## Three-layer verdict

**Social amplification: SUPPORTED.** Corrected H1–H3 pass their frozen
engineering thresholds.

**Functional organization: PARTIAL.** Corrected competence complementarity and
competence-aligned routing pass, but H6 does not establish robust realized team
utility improvement.

**Emergent functional specialization: NOT YET SUPPORTED.** The result is evidence
of private-history-dependent competence interaction and organized allocation, not
proof of stable identities or a useful division of labor.

## Strongest supported result

Adaptive competence-sensitive routing with private developmental histories
amplified held-out agent×niche competence interactions relative to random-private
and adaptive-shared controls in this eight-seed pilot.

## Strongest remaining null

The realized last-32 online team-utility gain remained below the preregistered
threshold, with AP12 positive in 6/8 seeds but mean gain only
0.007812.

## What this does not establish

This does not establish permanent roles, a phase transition, generalization beyond
the V3.1 DIAGONAL ecology, or causal superiority of private memory in every
environment. The independent units remain eight seeds, not 47,104 API calls.

## Outputs

Corrected machine-readable outputs are in
`reports/society/minimal-developmental-society-v1-analysis-repair/`; the old report
is explicitly superseded. No new experiment is authorized by this repair.
