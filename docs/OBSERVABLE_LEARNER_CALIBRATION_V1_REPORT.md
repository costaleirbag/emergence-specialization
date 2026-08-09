# Observable Ecology Learner Calibration V1

## Executive result

**PARTIAL LEARNER GEOMETRY — not qualified for a society experiment.** V3.1 was
verified locally and the Direct run was technically clean, but DeepSeek did not
realize the preregistered geometry strongly enough to pass gates A–H.

This is a learner-calibration result, not evidence about society specialization.

## Protocol and health

- DeepSeek Direct, `deepseek-v4-flash`, thinking off.
- GLOBAL/BLOCK/DIAGONAL; paired environment seeds 9201–9204.
- Natural teacher-correct feedback-only histories, h=8; six balanced held-out
  evaluation probes per target cell.
- 288 empty-memory baselines + 1,152 transfer contexts = 1,440 logical calls.
- 1,440 physical attempts; zero retries; zero semantic OOD; 100% usage coverage.
- One provider fingerprint; observed cost US$0.02681214 of US$0.20; mean/median
  latency 1.083/1.057 s.

Raw events are in `data/auto-research/observable-learner-calibration-v1/` and
derived tables in `reports/task-ecology/observable-learner-calibration-v1/`.

## Realized transfer geometry

`L^DeepSeek` is held-out exact three-decision accuracy after source exposure
minus the reused empty-memory baseline, averaged over four environment seeds.

| geometry | D (diag) | O (off-diag) | Q=D−O | O/D | Q(L*_obs) |
|---|---:|---:|---:|---:|---:|
| GLOBAL | +0.0833 | −0.0556 | +0.1389 | −0.667 | 0.0000 |
| BLOCK | +0.1042 | −0.0104 | +0.1146 | −0.100 | +0.5756 |
| DIAGONAL | +0.0208 | −0.0833 | +0.1042 | −4.000 | +0.8633 |

For BLOCK, within-block off-diagonal transfer was approximately 0.0000 and
cross-block transfer −0.0156, giving `B=0.0156` (below +0.05). The observed Q
ordering is **GLOBAL > BLOCK > DIAGONAL**, reverse to preregistration.

## Bayes opportunity versus realized response

`L*_obs` is roughly 0.86 in positive structured cells, while realized gains are
small. Raw matrix cosine (`L^DeepSeek`, `L*_obs`) was −0.246 (GLOBAL), +0.393
(BLOCK), and +0.091 (DIAGONAL). Centered cosine was undefined for GLOBAL (the
theoretical centered matrix is zero), and +0.643/+0.763 for BLOCK/DIAGONAL.
Projection alpha was −0.024/+0.060/+0.024. These are descriptive projections.

Zero-information cells had mean realized transfer −0.0563 with 30% positive
cell means: learner-/prior-induced or contextual effects, not ecological
transfer. Mean missed Bayes opportunity over 48 cells was +0.5236.

## Qualification gates

| gate | status |
|---|---|
| A GLOBAL diagonal learning ≥ .10 | FAIL |
| B BLOCK diagonal learning ≥ .10 | PASS |
| C DIAGONAL diagonal learning ≥ .10 | FAIL |
| D GLOBAL density O/D ≥ .50 | FAIL |
| E BLOCK structure B ≥ .05 | FAIL |
| F DIAGONAL locality O/D ≤ .50 | PASS |
| G Q_GLOBAL < Q_BLOCK < Q_DIAGONAL | FAIL |
| H directional geometry alignment | FAIL |

The fixed classification is **PARTIAL**. Component tables and anchoring
diagnostics are machine-readable in the report directory; joint exact accuracy
remains primary. No response is treated as an independent replication.

## Interpretation and limits

The clean run shows that observable Bayes opportunity is not automatically
realized by this model after eight natural semantic examples. Compatible causes
include weak rule learning, joint-output composition limits, context
interference, and a pretrained prior unlike `p_E`. This does not establish that
the model cannot learn the ecology at another horizon or representation.

No routing, private/shared memory, HSE, useful division of labor, persistence,
or social feedback was tested. `T(L)` remains a derived object of an explicit
effective model, not an LLM-society Jacobian. No paid follow-up is authorized;
the next step is principal-researcher review.
