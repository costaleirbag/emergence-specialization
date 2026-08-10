# Local Plasticity Curve V1 Report

## Executive result

**LOCAL PLASTICITY QUALIFIED (microscopic gate only).**

The frozen DIAGONAL-only campaign completed all **2,176/2,176** logical
completions with 2,176 physical attempts, zero technical retries, zero semantic
OOD responses, 100% usage coverage, and observed configured cost
**US$0.0555897104** against the US$0.12 ceiling. The model was
`deepseek-v4-flash` for every event.

The contemporaneous curves are:

| condition | h=0 | h=1 | h=2 | h=4 | h=8 |
|---|---:|---:|---:|---:|---:|
| SAME | .1250 | .1563 | .1875 | .2422 | **.3984** |
| FOREIGN | .1250 | .1328 | .1302 | .1458 | **.1068** |

At h=8:

```text
G_abs  = A_same - A0       = +0.2734
G_rel  = A_same - A_foreign= +0.2917
G_foreign = A_foreign-A0   = -0.0182
```

The positive local gain is therefore not explained only by harming the foreign
condition: same-niche exposure improves competence substantially, while foreign
context is slightly harmful at h=8.

## Why the project returned to the minimal hypothesis

The stronger cross-domain branch established that relation cues alone did not
control transfer, semantic correspondence helped, canonical representation
approximately restored local-level performance, and explicit rules were almost
perfectly executable. Those are informative learner diagnostics, but broad
GLOBAL/BLOCK/DIAGONAL transfer geometry is not required for the original minimal
developmental question.

The current result asks only whether a local positive-feedback substrate exists:

```text
experience in niche c -> useful competence in niche c
same-niche experience > equally sized independent foreign experience
```

The cross-domain branch is therefore closed as **informative but nonessential**
to the next minimal hypothesis, not as a failed research direction.

## Scientific question and protocol

- ecology: V3.1 `DIAGONAL` only;
- seeds: 9201–9204;
- niches: ACCESS, INCIDENT, PROVENANCE, RELEASE;
- histories: exact corrected V2 natural h=8 histories, original order;
- horizons: strict prefixes h∈{1,2,4,8};
- probes: exact V2 eight balanced, history-disjoint evaluation probes;
- output: exact three-bit joint correctness with the neutral V2 harness;
- model: DeepSeek Direct `deepseek-v4-flash`, thinking off;
- primary unit: environment seed, n=4.

No GLOBAL, BLOCK, relation cue, correspondence, canonicalization, explicit rule,
teaching history, routing, or society was used.

## Technical health

| field | value |
|---|---:|
| logical expected / terminal | 2,176 / 2,176 |
| physical attempts | 2,176 |
| technical retries | 0 |
| semantic OOD | 0 |
| completion coverage | 100% |
| usage coverage | 100% |
| model | `deepseek-v4-flash` |
| provider fingerprint | `fp_a18b46594c_prod0820_fp8_kvcache_20260402` |
| mean / median latency | 1.1134 s / 1.0865 s |
| observed cost | US$0.0555897104 |
| classification | `CLEAN` |

## Empty-memory competence

The aggregate exact joint baseline was `A0=.1250`, the ecology-prior Bayes
baseline. Seed baselines were `.1875, .0625, .0625, .1875`; these four values
are repeated-measurement summaries, not four independent model calls.

## Same-niche plasticity curve

`A_same(h)` increased at every frozen horizon: `.1563 → .1875 → .2422 → .3984`.
The descriptive log-dose slope was **+0.1101** aggregate. Seed slopes were
`+0.1626, +0.0272, +0.1452, +0.1055`; 3/4 exceed zero. `A_same(8)-A_same(1)
= +.2422`.

The h8 same-niche gain by seed was:

| seed | G_abs(8) |
|---:|---:|
| 9201 | +.2813 |
| 9202 | +.1563 |
| 9203 | +.4063 |
| 9204 | +.2500 |

## Foreign-niche control curve

`A_foreign(h)` stayed near baseline at h=1–4 and fell to `.1068` at h=8. The
foreign-context effects were `+.0078, +.0052, +.0208, -.0182`; the h8 value is
slightly harmful, but the interpretation remains a control diagnostic rather
than a claim of ecological transfer.

## Absolute and relative plasticity

| h | G_abs | G_rel | G_foreign |
|---:|---:|---:|---:|
| 1 | +.0313 | +.0234 | +.0078 |
| 2 | +.0625 | +.0573 | +.0052 |
| 4 | +.1172 | +.0964 | +.0208 |
| 8 | **+.2734** | **+.2917** | -.0182 |

Integrated over h={1,2,4,8}:

- `I_abs = +.1211`;
- `I_rel = +.1172`.

The h8 relative gains by seed were `+.2917, +.1771, +.3438, +.3542`.

## Component-level behavior

At h=8:

| component | A0 | SAME | FOREIGN | G_abs | G_rel |
|---:|---:|---:|---:|---:|---:|
| 1 | .4453 | .6641 | .5052 | +.2188 | +.1589 |
| 2 | .5703 | .7500 | .4792 | +.1797 | +.2708 |
| 3 | .4766 | .6953 | .4609 | +.2188 | +.2344 |

All three components have positive absolute gains and all exceed the .05
component threshold.

## Niche heterogeneity

| target | A0 | SAME h8 | FOREIGN h8 | G_abs | G_rel |
|---|---:|---:|---:|---:|---:|
| ACCESS | .2188 | .3125 | .1458 | +.0938 | +.1667 |
| INCIDENT | .1250 | .3750 | .0729 | +.2500 | +.3021 |
| PROVENANCE | .0938 | .5000 | .1146 | +.4063 | +.3854 |
| RELEASE | .0625 | .4063 | .0938 | +.3438 | +.3125 |

All niches show positive h8 local gain. ACCESS is the weakest absolute case;
PROVENANCE is strongest. This heterogeneity is scientifically relevant and was
not filtered.

## Bayes opportunity versus realized learning

The exact frozen ecology audit gave:

| condition | h=0 | h=1 | h=2 | h=4 | h=8 |
|---|---:|---:|---:|---:|---:|
| Bayes SAME | .1250 | .4190 | .5470 | .7793 | .9844 |
| Bayes FOREIGN | .1250 | .1250 | .1250 | .1250 | .1250 |

The model realizes only part of the Bayes opportunity, but this experiment does
not gate on Bayes efficiency. Its relevant result is that the realized SAME
curve is positive and selective relative to FOREIGN.

## Anchoring diagnostics

At h=8, any-memory full-action copying was .8125 for SAME and .8516 for
FOREIGN; last-action copying was .1953 and .2161. Correctness conditional on
any-memory copying was .3654 for SAME versus .5417 when not copied, and .1040
for FOREIGN versus .1228 when not copied. This does not eliminate anchoring as
a mechanism, but it argues against interpreting the local gain as simple
successful label copying alone.

## Historical V2 replication

Historical V2 DIAGONAL aggregates were:

| quantity | V2 | current |
|---|---:|---:|
| A0 | .1641 | .1250 |
| SAME h8 | .3516 | .3984 |
| FOREIGN h8 | .1302 | .1068 |
| G_abs h8 | .1875 | .2734 |
| G_rel h8 | .2214 | .2917 |

The current result is **directionally replicated**: local experience helps and
foreign context does not. Exact equality is not expected from one provider
completion per prompt and stochastic API calls.

## L1–L6 qualification

| gate | result |
|---|---|
| L1 useful h8 absolute learning | PASS |
| L2 h8 local selectivity | PASS |
| L3 integrated useful learning | PASS |
| L4 integrated local selectivity | PASS |
| L5 dose direction | PASS |
| L6 component sanity | PASS |

All six preregistered gates passed. With n=4 environment seeds, this is a
qualification gate, not population-level statistical evidence.

## Minimal substrate verdict

- useful absolute learning: **YES**;
- niche-selective learning: **YES**;
- dose-responsive learning: **YES, descriptively**;
- local plasticity: **QUALIFIED**.

This means a minimal social feedback experiment is scientifically defensible to
design. It does not mean that specialization has emerged, that routing will
amplify it, or that private memory is causal.

## Adversarial caveats

- Four environment seeds are a small qualification sample.
- Each prompt received one provider completion; model stochasticity is not
  separately replicated.
- The feedback histories are teacher-correct resolved cases, stronger and
  cleaner than a society's endogenous feedback stream.
- Foreign memory slightly harms performance at h8, so `G_rel` must not be read
  as pure local learning without `G_abs`.
- Exact three-bit composition remains multiplicative; component gains do not
  prove a reusable symbolic rule.
- The ecology is synthetic and semantic; external validity is untested.

The return to this minimal experiment is principled, not merely a retreat from
the stronger theory: the original causal question requires local plasticity,
while broad transfer geometry is a separate extension.

## Society-entry recommendation

The society gate is **OPEN FOR DESIGN ONLY**. Do not run it automatically.

The next design should be minimal and preregistered: four initially exchangeable
agents, four DIAGONAL niches, exact verifier, natural task stream, and controls
for adaptive confidence routing + private memory, random routing + private
memory, and adaptive routing + shared memory. The primary question should be
whether competence-sensitive allocation amplifies accidental competence
differences more than controls. HSE remains secondary.

No society was executed in this phase.
