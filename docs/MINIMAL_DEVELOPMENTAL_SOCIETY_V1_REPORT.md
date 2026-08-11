# Minimal Developmental Society V1 report

## Executive result

The paid campaign and offline analysis are **complete**. The preregistered result
is **not evidence of emergent functional specialization**: social amplification
(H1/H3), complementarity (H4), and team-utility gain (H6) did not meet their
engineering criteria. Private state was necessary for the observed competence
interaction contrast (H2), and AP12 showed organized routing relative to its
permutation null (H5). These are separate findings, not a claim of stable roles.

## Protocol

Four initially exchangeable agents operated in the V3.1 DIAGONAL ecology for 128
balanced online tasks with bounded host-side recent-k=8 memory. The four frozen
regimes were RP, AP4, AP12, and AS12. Held-out evaluation occurred at checkpoints
0, 16, 32, 64, 96, and 128. Routing used externally verified online exact-joint
correctness; model confidence was not requested.

## Technical health and cost

- Logical completions: **47104 / 47104**
- Physical attempts: **47109**; retries: **5**
- Semantic out-of-domain observations: **4** (terminal, not retried)
- Error categories: `{"out_of_domain": 4, "parse_error": 2, "transient_transport": 2, "usage_unavailable": 1}`
- Terminal model: `['deepseek-v4-flash']`
- Terminal fingerprint: `['fp_a18b46594c_prod0820_fp8_kvcache_20260402']`
- Usage coverage: **0.999936**
- Latency mean/median/min/max: **1.176 / 1.111 / 0.671 / 376.636s**
- Observed cost: **US$1.140245** (cap US$2.25)
- Health: **COMPLETE_WITH_RETRIES**

The missing-usage incident was repaired conservatively before resumption. No
logical observation was duplicated and no model identity mismatch occurred.

## Primary order parameter

`Psi_spec(A) = ||P_N A P_K||_F^2/(N*K)` measures the agent×niche competence
interaction after removing agent and niche main effects. It is not equivalent to
HSE, total competence differentiation (`Phi`), routing concentration, or useful
division of labor.

| regime | final Psi_spec bit | final Phi bit | final matching gain (joint) |
|---|---:|---:|---:|
| RP | 0.002786 | 0.010598 | -0.064453 |
| AP4 | 0.004011 | 0.016948 | -0.078125 |
| AP12 | 0.004886 | 0.014097 | -0.054688 |
| AS12 | 0.001087 | 0.004551 | -0.070312 |

The main contrasts were AP12−RP Psi mean **0.002100**
(6/8 positive), AP12−AS12 **0.003799**
(8/8 positive), and AP12−RP AUC **0.001199**
(6/8 positive). H1 and H3 remained below their preregistered thresholds.

## Organization, complementarity, and utility

- H4 complementarity: AP12 matching gain mean **-0.054688**; AP12−RP **0.009766** — **not supported**.
- H5 routing organization: AP12 excess task–agent information **0.269009** bits and late routing alignment η **0.229408** — supported by the engineering rule, but not sufficient for specialization.
- H6 team utility: AP12−RP last-32 accuracy **0.007812**, positive in 6/8 seeds — **not supported**.

## Interpretation and limitations

Private controlled state changes the trajectory and AP12 can organize allocation
around niches, but this campaign did not show that organization becoming a stable,
useful division of labor. High routing information can coexist with weak or
negative matching gain. The independent units are eight environment seeds, not
47,104 API calls. Provider stochasticity, finite horizon, recent-k capacity,
teacher-correct feedback, and the single DIAGONAL ecology limit generality. No
claim of permanent identities or a phase transition is licensed.

All per-seed trajectories, health data, costs, and figures are in
`reports/society/minimal-developmental-society-v1/`. No further paid calls were
made after campaign completion.
