# Relation-Signal Causal Transfer V1

**Final status: PARTIAL RELATION CONTROL.** The campaign was technically clean,
but the preregistered learner-geometry qualification gates were not met. This
was a learner-level intervention; no society was run.

## Executive result

DeepSeek Direct completed all 3,456 frozen logical tasks with 3,456 physical
attempts, zero technical retries, two semantic out-of-domain observations, and
US$0.089407 observed configured cost. The provider model was
`deepseek-v4-flash` for every event and usage was present for every attempt.

The relation cue produced only a near-zero source-policy contrast:

| quantity | value |
|---|---:|
| `Gamma_R` (high-identifiability) | -0.0072 |
| `Delta_same` | +0.0078 |
| `Delta_independent` | -0.0109 |
| `Upsilon_R` | -0.0016 |
| `RS` same-relation accuracy | 0.1602 |
| historical V2 `R_NONE` cross accuracy | 0.1502 |
| `RS - R_NONE` | +0.0100 |

The small `RS`–`R_NONE` difference does not establish relation inference. All
gates except the broad relation-oracle alignment gate failed.

## Scientific question and hierarchy

The frozen question was whether a minimal learner-visible statement about the
source/target policy relation changes realized cross-domain transfer while the
history and target case remain fixed. The intended hierarchy is:

```text
G -> J_obs / L*_obs -> L^DeepSeek -> (future) social dynamics
```

This campaign ends at `L^DeepSeek`. It does not test specialization, routing,
feedback locality, or a society.

## Frozen protocol

- DeepSeek Direct, `deepseek-v4-flash`, thinking off.
- Seeds 9201–9204; geometries GLOBAL, BLOCK, DIAGONAL.
- Natural resolved h=8 V2 histories; eight held-out V2 probes.
- 1,152 cross-domain underlying tasks × R0/RS/RI = 3,456 new calls.
- R0 was no relation statement; RS stated same policy; RI stated independent
  policy. The cue was inserted before the unchanged V2 history renderer.
- Existing V2 cross-domain responses were reused as historical `R_NONE`.
- Same-family diagonals in the truthful-R matrix were reused from V2; no new
  same-family calls were made.
- The independent scientific unit is environment seed (`n=4`), not API call.

Source-policy identifiability passed its precondition: 1,116/1,152 underlying
tasks (96.875%) had `A*_source >= .99`.

## Technical health

The raw journal and machine-readable health report reconcile exactly:

| field | value |
|---|---:|
| logical expected / terminal | 3,456 / 3,456 |
| physical attempts | 3,456 |
| technical retries | 0 |
| semantic OOD | 2 |
| completion coverage | 100% |
| usage coverage | 100% |
| model | `deepseek-v4-flash` |
| fingerprint | `fp_a18b46594c_prod0820_fp8_kvcache_20260402` |
| observed cost | US$0.089407 |

The two OOD outputs were retained as terminal scientific observations and were
not given a second chance. No further external inference is authorized.

## Cue-arm and source-policy results

On high-identifiability tasks, RS source-policy adherence was approximately
0.161 on actual SAME_POLICY cells and 0.145 on INDEPENDENT_POLICY cells. The
high-identifiability `RS - RI` contrast was negative overall (`Gamma_R=-0.0072`)
and positive in only two of four seeds (+0.0069 and +0.0198).

The response-level source-policy signal is therefore not evidence that the
model followed the cue to apply the source policy. Exact output accuracy stayed
near the low cross-domain baseline.

## Truthful-R transfer geometry

The truthful matrix combines V2 same-family diagonals with RS on actual
same-policy cross pairs and RI on actual independent cross pairs.

| geometry | D | O | Q=D−O | W | C | B=W−C |
|---|---:|---:|---:|---:|---:|---:|
| GLOBAL | 0.2578 | -0.0599 | 0.3177 | -0.0703 | 0.0000 | -0.0703 |
| BLOCK | 0.2188 | 0.0000 | 0.2188 | 0.0234 | -0.0117 | 0.0352 |
| DIAGONAL | 0.1875 | -0.0339 | 0.2214 | -0.0078 | -0.0339 | 0.0260 |

The preregistered ordering `Q_GLOBAL < Q_BLOCK < Q_DIAGONAL` was **not**
observed (`0.3177 > 0.2188 > 0.2214`). BLOCK's `B=0.0352` was positive but
below the +0.05 gate. These are descriptive realized transfer values, not proof
of functional specialization.

Per-seed contrasts are in `seed_level_contrasts.csv` and
`truth_interaction.csv`; no response-level row is treated as an independent
replicate.

## Bayes opportunity versus realized response

The descriptive projection coefficient onto the relation-aware Bayes opportunity
was `alpha = 0.0845`; mean missed transfer was `0.4694`. There were 20 zero-
relation-opportunity cells, with mean realized transfer `-0.0250`. These values
indicate that DeepSeek realized only a small projection of the available
relation-conditioned opportunity under this interface. The residual is not
causal noise: it can include pretrained semantic coupling, generic context
effects, anchoring, and response noise.

Aggregate raw relation-oracle cosines were positive for BLOCK (0.6460) and
DIAGONAL (0.7720), but weaker for GLOBAL (0.1242); centered cosines were 0.6412
and 0.9357 for BLOCK and DIAGONAL (GLOBAL is degenerate after centering). The
positive alignment gate alone is not sufficient to claim learner geometry
qualification because the other preregistered gates failed.

## Secondary diagnostics

Component-level exact learning was uneven: for RS on actual SAME_POLICY cells,
component accuracies were approximately 0.587, 0.560, and 0.511; joint exact
accuracy remained 0.160. Output distributions were broad (about 2.9 bits of
joint-output entropy), with two invalid/OOD RS responses.

Any-memory action-copy rates were high (R0 0.867, RS 0.877, RI 0.885) and
last-action copy rates were 0.257, 0.265, and 0.274 respectively. This is an
important confound: positive transfer-like cells can reflect copying or generic
context behavior rather than reusable policy induction.

## Qualification gates

| gate | result |
|---|---|
| R1: `Gamma_R >= .10`, ≥3/4 positive seeds | FAIL |
| R2: same-relation RS gain and above R_NONE | FAIL |
| R3: high-identifiability RS source adherence ≥ .30 | FAIL |
| R4: `Upsilon_R >= .10`, ≥3/4 positive seeds | FAIL |
| R5: BLOCK `W>0`, `B>=.05` | FAIL |
| R6: required Q ordering | FAIL |
| R7: positive relation-oracle alignment | PASS (insufficient alone) |

Classification: **PARTIAL RELATION CONTROL**, not established.

## Interpretation

The intervention is technically successful and shows that the harness can vary a
relation sentence without changing the frozen semantic history. It does not show
that DeepSeek reliably uses the sentence to apply a source policy. The strongest
supported conclusion is narrower: under this prompt, h=8 natural histories, and
one completion per probe, realized transfer was weak and largely did not track
the preregistered relation cue. The positive BLOCK/DIAGONAL matrix alignment is
descriptive and insufficiently consistent to support a society entry gate.

This result does not distinguish among weak semantic relation parsing, insufficient
context, joint three-bit composition limits, pretrained priors, and anchoring.
Those are follow-up hypotheses only. Do not tune the prompt or run a society
automatically.

## What this does not establish

- It does not establish spontaneous specialization or useful division of labor.
- It does not establish that the V3.1 ecology is non-learnable in general.
- It does not establish that DeepSeek cannot learn relation structure with a
  different interface; that would be a different preregistered experiment.
- It does not justify adding seeds, changing h, enabling thinking, or running
  Gate 2 without principal-researcher review.

## Artifacts

Authoritative outputs:

`reports/task-ecology/relation-signal-causal-transfer-v1/`

Key files include the frozen manifest, raw response-level table, arm summaries,
source-policy adherence, seed contrasts, truthful-R matrices, geometry metrics,
relation alignment, component and anchoring diagnostics, projection/residual
tables, technical health, cost, and figures.
