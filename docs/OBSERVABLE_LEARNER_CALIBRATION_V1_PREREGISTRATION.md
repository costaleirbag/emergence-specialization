# Observable Ecology Learner Calibration V1

Status: frozen single-agent qualification gate; no society or routing experiment.

## Question and hierarchy

The V3.1 ecology fixes the observable information geometry before inference. This
gate measures the realized DeepSeek transfer matrix `L^DS` and compares it with
the already materialized `J_obs` and `L*_obs` tables. The hierarchy is

`G -> J_latent -> J_obs -> L*_obs -> L^DeepSeek`.

Only the final arrow is measured here. `T(L^DeepSeek)` and society organization
are future, untested objects.

## Frozen protocol

- Provider: DeepSeek Direct; model: `deepseek-v4-flash`; thinking: off.
- Four environment seeds: `9201, 9202, 9203, 9204`. They are outside the V3/V3.1
  reported seed sequences and are paired across all geometries.
- Geometries: `GLOBAL`, `BLOCK`, `DIAGONAL`.
- Families: `ACCESS`, `RELEASE`, `INCIDENT`, `PROVENANCE`.
- Natural teacher-correct, feedback-only histories of exactly `h=8`.
- Six held-out evaluation-template probes per target family, per geometry/seed.
  Each component is balanced 3/3; probes are disjoint from all four source
  histories for that environment.
- One Direct completion per exact prompt. Environment seed is the scientific
  unit (`n=4`); responses are repeated measurements, not independent samples.
- Empty-memory baselines are called once and reused for every source condition
  within a geometry/seed/target/probe cell.
- Model-facing prompts contain only V3.1 semantic cases and resolved decisions.
  They contain no family IDs, geometry, seed, theta, canonical factor, model
  prediction, confidence, explanation, or chain of thought.
- Output schema: exactly `{"decisions":[0,1,0]}` (three binary decisions).

## Call budget and retry semantics

Baseline calls: `3 * 4 * 4 * 6 = 288`.

Transfer calls: `3 * 4 * 4 * 4 * 6 = 1,152`.

Total: **1,440 logical completions**. Technical retries are bounded at one per
logical context (maximum 2 physical attempts). Empty/transport/rate-limit/server
and malformed JSON responses are technical retry candidates. A syntactically
valid object with an invalid decision domain is a completed scientific
out-of-domain observation and is never retried. The hard new external ceiling is
US$0.20 including retries. The preflight forecast must satisfy
`1.5 * projected_nominal <= 0.20` before credentials are read.

## Primary outcomes and fixed gates

For each geometry and seed, `L^DS_cd` is transfer exact-joint accuracy minus the
reused empty-memory accuracy. Report all twelve 4x4 matrices and their aggregate.

1. `D_DS_GLOBAL`, `D_DS_BLOCK`, and `D_DS_DIAGONAL` (mean diagonal gain) each
   must be at least `+0.10`.
2. `R_GLOBAL = O/D >= 0.50`.
3. `B_BLOCK = W - C >= +0.05`.
4. `R_DIAGONAL = O/D <= 0.50` when `D>0`.
5. `Q_GLOBAL < Q_BLOCK < Q_DIAGONAL`, where `Q=D-O`.
6. Raw/centered alignment with `L*_obs` must be directionally positive and not
   entirely driven by one seed.

All gates are qualification engineering criteria, not p-value thresholds. A
failure means no follow-up paid experiment and no society run.

## Secondary analyses

Component-level gains, baseline balance, zero-`J_obs` learner-induced transfer,
missed Bayes opportunity, Frobenius projection `alpha`, residual structure,
semantic-family effects, and last/any-memory action anchoring are descriptive.
Provider metadata, latency, usage, retries, OOD responses, and cost are retained
at response level.

## Interpretation table

| Result | Interpretation |
|---|---|
| Positive diagonal and predicted geometry | DeepSeek realizes part of the observable ecology's transfer geometry; society remains untested. |
| Positive zero-`J_obs` cells | Learner-induced/prior-induced transfer, not ecological transfer. |
| Weak diagonal | Observable task is not sufficiently learnable for this model/horizon, or context interferes. |
| Flattened geometry | Model prior/semantic analogy overwhelms ecology. |
| Qualification failure | Return for principal review; do not tune prompts, add seeds, or switch model. |

## Limitations fixed in advance

Six probes and four seeds are a pilot gate; one provider completion leaves model
stochasticity unresolved. Teacher-correct feedback is a controlled learner
calibration, not a claim about endogenous society feedback. The three-bit output
is exact but artificial. A positive transfer gain can also reflect context
length, anchoring, or pretrained semantic coupling, especially in zero-`J_obs`
cells. The Bayes learner's ecology prior `p_E` is not assumed to equal DeepSeek's
pretrained prior `q_m`.

## No-go decisions

No society, Gate 2, routing, thinking-on run, additional seed, prompt tuning,
teaching-history campaign, model switch, or paid follow-up is authorized by this
preregistration.
