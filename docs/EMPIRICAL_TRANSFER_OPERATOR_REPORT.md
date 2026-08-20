# Empirical transfer-operator report — TRANSFER-GEOMETRY-CONTROL-V1

**Status:** complete; offline analysis of the frozen single-agent campaign. This
is a task-ecology calibration, not an LLM-society result.

## Executive summary

The campaign completed all three preregistered geometries (GLOBAL, BLOCK,
DIAGONAL), five environment seeds, and 11,520 logical completions. The natural
exposure matrix `L_nat` is the primary result; teaching is a positive-control
upper bound. All logical units are covered. GLOBAL contains one recovered
technical parse retry and one terminal semantic out-of-domain response; BLOCK
and DIAGONAL each contain one terminal semantic out-of-domain response and no
technical retries.

The designed geometry was not cleanly recovered by natural transfer at this
sample size. Natural diagonal locality was positive (`Q=0.0479`) but only
slightly above BLOCK (`0.0375`) and GLOBAL (`0.0313`), with paired geometry
contrasts changing sign across seeds. Teaching increased locality most in
GLOBAL (`Q=0.1125`) and BLOCK (`0.0771`) and slightly decreased it in DIAGONAL
(`0.0344`); this is the opposite of the preregistered expectation that the
designed geometry would rank directly by locality. The control therefore does
not establish a predictive designed-geometry-to-learning law. It does establish
that the ecology can be measured reproducibly and that the proposed controls
can fail informatively.

## Frozen protocol and technical accounting

| item | value |
|---|---|
| backend/model | DeepSeek Direct / `deepseek-v4-flash` |
| thinking | off |
| geometries | GLOBAL, BLOCK, DIAGONAL |
| environment seeds | 8101–8105 |
| families | ACCESS, RELEASE, INCIDENT, PROVENANCE |
| probes/family | 8 |
| replicates/probe | 2 |
| logical calls/geometry | 3,840 |
| total logical calls | 11,520 |
| physical attempts | 11,521 |
| observed cost | US$0.240807868 |
| hard cap | US$1.50 |
| budget reservation at finish | US$0.00 |

Per-geometry health:

| geometry | logical | physical | technical retries | retry category | semantic OOD | cost (USD) |
|---|---:|---:|---:|---|---:|---:|
| GLOBAL | 3,840 | 3,841 | 1 | parse_error | 1 | 0.087910732 |
| BLOCK | 3,840 | 3,840 | 0 | — | 1 | 0.0817363904 |
| DIAGONAL | 3,840 | 3,840 | 0 | — | 1 | 0.0711607456 |

The recovered parse error was retried as a technical failure. The three
out-of-domain answers remained completed, incorrect scientific observations;
none received a second chance. Provider identity was `deepseek-v4-flash` for
every recorded attempt. No duplicate terminal logical IDs were found.

Recorded inference latency was usually short but had a long tail:

| geometry | mean (s) | median (s) | p95 (s) | max (s) |
|---|---:|---:|---:|---:|
| GLOBAL | 1.131 | 1.077 | 1.622 | 5.587 |
| BLOCK | 1.035 | 1.014 | 1.275 | 1.871 |
| DIAGONAL | 1.156 | 1.060 | 1.615 | 128.311 |

The DIAGONAL tail is an infrastructure/runtime observation, not a semantic
finding; it was preserved rather than hidden or retried as a scientific unit.

## Estimand

For source family `c`, target family `d`, and eight experiences,

`L_cd(8) = accuracy_d(after exposure to c) - accuracy_d(empty memory)`.

The four-by-four matrices are SOURCE × TARGET. `L_nat` uses the frozen ordinary
train pool and is primary. `L_teach` uses the frozen greedy predictive-
identifiability stream as a positive control. The h=4 diagonal and foreign-
theta controls are retained in the per-family tables.

Machine-readable outputs are in
`reports/task-ecology/transfer-geometry-v1/`:

- `environment_level_L.csv`: every seed, source, target, and policy;
- `aggregate_L.csv`: long-form matrices;
- `transfer_metrics.csv`: per-seed `D`, `O`, `Q`, `E_T`, `chi`, `r_eff`, `A_dir`;
- `alignment.csv`: designed-to-observed alignments;
- `theta_specificity_full.csv`: same- versus foreign-theta contrasts;
- `nonnormal_diagnostics.csv`, `toy_dynamics.csv`, and `robustness.csv`.

## Aggregate transfer geometry

Means over the five environment seeds are shown below. They are descriptive
summaries, not population estimates.

| geometry | policy | D | O | Q=D−O | E_T | chi | r_eff | A_dir |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| GLOBAL | natural | 0.1500 | 0.1188 | 0.0313 | 0.0945 | 0.0411 | 1.968 | 0.687 |
| BLOCK | natural | 0.0781 | 0.0406 | 0.0375 | 0.0842 | 0.0519 | 2.027 | 0.480 |
| DIAGONAL | natural | 0.1125 | 0.0646 | 0.0479 | 0.0822 | 0.0375 | 2.147 | 1.008 |
| GLOBAL | teaching | 0.2156 | 0.1031 | 0.1125 | 0.0955 | 0.0591 | 1.946 | 0.579 |
| BLOCK | teaching | 0.1000 | 0.0229 | 0.0771 | 0.0827 | 0.0416 | 1.860 | 0.677 |
| DIAGONAL | teaching | 0.1063 | 0.0719 | 0.0344 | 0.0807 | 0.0351 | 2.026 | 0.806 |

The teaching-minus-natural gap in `Q` is +0.0813 (GLOBAL), +0.0396 (BLOCK),
and −0.0135 (DIAGONAL). Thus teaching demonstrates that the model can respond
to some selected exposure streams, but it does not validate the intended
geometry ordering.

The natural per-seed `Q` contrasts are not stable: DIAGONAL minus GLOBAL is
positive in 3/5 seeds and negative in 2/5; BLOCK minus GLOBAL is positive in
2/5 and negative in 3/5. Leave-one-seed-out natural `Q` remains positive within
each geometry, but that does not imply a reliable between-geometry ordering.

## Designed geometry versus measured geometry

The designed overlap matrices were exact by construction: GLOBAL had 2/3
off-diagonal overlap, BLOCK had 2/3 within-block and zero cross-block overlap,
and DIAGONAL had zero off-diagonal overlap. Natural alignment was modest by
directed/off-diagonal measures:

| geometry | natural Spearman(G,L) | natural centered Frobenius | natural normalized spectral |
|---|---:|---:|---:|
| GLOBAL | 0.217 | 0.226 | 0.869 |
| BLOCK | 0.203 | 0.505 | 1.000 |
| DIAGONAL | 0.182 | 0.378 | 0.992 |

The high normalized spectral values should not be over-read: this diagnostic is
a cosine between short spectra after centering, and is not a test that the
entrywise transfer pattern recovered the designed factors. Teaching alignments
were generally higher in centered Frobenius cosine (0.694, 0.683, 0.448 for
GLOBAL, BLOCK, DIAGONAL), but the teaching `Q` ordering was also inconsistent
with the preregistered prediction.

**Protocol prediction check:**

- GLOBAL should have denser off-diagonal transfer and weaker locality: partly
  supported descriptively, but its natural `D` and `Q` were not the smallest.
- BLOCK should have within-block transfer greater than cross-block transfer:
  its aggregate natural `B` was positive, but the paired `Q` ordering was not
  stable.
- DIAGONAL should have the strongest comparative advantage: not established;
  its natural `Q` was largest only in the five-seed mean by a small margin.

No post hoc reinterpretation of a geometry was used.

## Foreign-theta specificity

The foreign-theta control compares natural h=8 exposure from an adjacent run's
latent factor values with same-theta exposure. Across all 20 seed-family cells:

| geometry | mean S_theta | median | range | positive cells |
|---|---:|---:|---:|---:|
| GLOBAL | 0.0469 | 0.0938 | [−0.3125, 0.2500] | 12/20 |
| BLOCK | 0.0813 | 0.0313 | [−0.1875, 0.3750] | 10/20 |
| DIAGONAL | 0.0219 | 0.0313 | [−0.2500, 0.3125] | 10/20 |

This is weak, variable evidence of run-specific theta dependence, not a clean
demonstration of procedural acquisition. It is also not a causal estimate of
learning: same- and foreign-theta streams can differ in surface examples and
baseline difficulty.

## Directionality and transient diagnostics

The aggregate directed matrices were materially asymmetric (`A_dir` about
0.48–1.01 for natural policies). For the explicit effective operator
`T=P L^T D_rho P`, the largest real eigenvalue, numerical abscissa, and maximum
finite-time amplification on the declared grid `t={0,.25,.5,1,2,4}` were:

| geometry | policy | max Re eig | numerical abscissa | max amplification | eigvec condition |
|---|---|---:|---:|---:|---:|
| GLOBAL | natural | 0.0467 | 0.0489 | 1.216 | 2.71 |
| BLOCK | natural | 0.0430 | 0.0446 | 1.195 | 4.26 |
| DIAGONAL | natural | 0.0343 | 0.0363 | 1.156 | 1.61 |
| GLOBAL | teaching | 0.0430 | 0.0596 | 1.269 | 6.13 |
| BLOCK | teaching | 0.0394 | 0.0399 | 1.173 | 2.12 |
| DIAGONAL | teaching | 0.0201 | 0.0211 | 1.088 | 3.27 |

These are properties of measured matrices and the explicit effective model.
They are not evidence that an LLM society follows this Jacobian. The modest
finite-time amplification is exploratory and should not be called persistent
specialization.

## Effective toy dynamics

The deterministic toy integration uses the frozen dimensionless grid
`kappa={0.25,0.5,1,2,4}`, a fixed small perturbation, and measured aggregate
`L`. Every row is labelled **EFFECTIVE TOY MODEL — NOT LLM SOCIETY DATA**.
Across this grid the linear growth rates remained negative (the largest was
still below zero), and the perturbation decayed. This is a result for the stated
relaxation/softmax toy model, not a prediction verified in a society.

## Robustness and limitations

- Five environment seeds are enough to expose instability of the geometry
  ordering, not enough for a definitive population claim.
- Two response replicates per probe are nested within each task context; they
  are not independent environment replicates.
- Accuracy is quantized in increments of 1/16 per seed-family cell.
- One OOD response per geometry is retained as an incorrect observation. The
  single recovered parse retry is represented once in the logical dataset.
- The natural/teaching contrast is not a causal estimate of an LLM learning
  algorithm; teaching changes the exposure stream and may change prompt
  identifiability.
- Foreign-theta specificity is vulnerable to example-surface and difficulty
  differences.
- `P L^T D_rho P` is a Jacobian only inside the explicit effective model and
  under its stated contrast-sector assumptions.
- Prompt-template shortcuts, answer priors, unequal task difficulty, and
  semantic family familiarity remain live threats.

## Reproducibility

The frozen task manifests are under
`reports/task-ecology/transfer-geometry-v1/manifests/`; raw append-only logs are
under `data/auto-research/transfer-geometry-v1/`. The offline commands are:

```bash
PYTHONPATH=src .venv/bin/python -m emergent_specialization.transfer_geometry --aggregate
PYTHONPATH=src .venv/bin/python -m emergent_specialization.transfer_analysis --run
```

Neither command performs network or model inference.
