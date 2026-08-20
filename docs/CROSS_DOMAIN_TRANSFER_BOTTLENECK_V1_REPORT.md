# Cross-Domain Transfer Bottleneck V1

**Status: PARTIAL DIAGNOSTIC — LEARNER GEOMETRY NOT QUALIFIED.**

This was a single-agent DeepSeek calibration ladder. It was not a society
experiment, and it does not authorize routing, feedback, or specialization
experiments.

## Executive result

The frozen campaign completed all **2,944/2,944 logical completions** with
2,944 physical attempts, no technical retries, one terminal semantic
out-of-domain response, 100% usage coverage, and observed configured cost
**US$0.0653269344** against the US$0.15 cap. Every provider record identified
`deepseek-v4-flash`.

The ladder localizes the bottleneck more sharply than the earlier relation cue:

| arm | interface | joint exact accuracy |
|---|---|---:|
| `LOCAL_REP` | same-family natural history, semantic target | 0.3802 |
| `A0_RELATION_ONLY` | cross-family + relation cue | 0.1526 (511 valid) |
| `A1_SEMANTIC_PI` | A0 + explicit semantic correspondence | 0.2598 |
| `A2_CANONICAL` | relation cue + canonical history/target representation | 0.4180 |
| `A3_RULE_SEMANTIC` | explicit true policy table + semantic target | 0.9941 |
| `A4_RULE_CANONICAL` | explicit true policy table + canonical target | 1.0000 |

The large `A2 -> A3` jump (`+0.5762`) and the near-zero `A3 -> A4` target
representation gap (`+0.0059`) indicate that target-side semantic execution is
not the dominant failure. The principal unresolved step is extracting and
executing a reusable policy from eight natural resolved examples, especially
across semantic domains. `A1-A0=+0.1071` shows that an explicit correspondence
helps, but the effect is below the preregistered robustness requirement in two
of four seeds.

## Scientific hierarchy

```text
G  ->  J_obs / L*_obs  ->  L^DeepSeek  ->  (future) social dynamics
```

This campaign measures only `L^DeepSeek`. `T(L^DeepSeek)` and any social
organization remain future, model-dependent objects.

## Frozen protocol and provenance

- protocol: `CROSS-DOMAIN-TRANSFER-BOTTLENECK-V1`
- model/provider: DeepSeek Direct, `deepseek-v4-flash`, thinking off
- seeds: 9201–9204; h=8; V2 histories/probes/templates reused exactly
- arms: `LOCAL_REP`, `A0_RELATION_ONLY`, `A1_SEMANTIC_PI`, `A2_CANONICAL`,
  `A3_RULE_SEMANTIC`, `A4_RULE_CANONICAL`
- expected calls: 384 local + 5×512 cross = 2,944
- execution commit frozen in manifest: `809b4ac0ad64ee45f11003112d4ce504c64a7831`
- task hash: `7baedc915d7f2a42864cb12ad06a094adf9ff7e1cf2c2b08440af6a981cfe419`
- source-policy identifiability: 868/896 underlying units = 0.96875
- no family IDs, geometry names, or explicit target answer vectors were present
  in model-facing prompts; A3/A4 intentionally supplied rule tables.

## Technical health

| field | result |
|---|---:|
| logical expected / terminal | 2,944 / 2,944 |
| physical attempts | 2,944 |
| technical retries | 0 |
| semantic OOD | 1 |
| completion coverage | 100% |
| usage coverage | 100% |
| observed cost | US$0.0653269344 |
| cap remaining | US$0.0846730656 |
| model identities | only `deepseek-v4-flash` |
| health class | `CLEAN` |

The OOD event was an `A0_RELATION_ONLY` response `{"decisions": []}`. It was
retained as an incorrect terminal scientific observation and was not retried.

## Ladder and seed contrasts

The aggregate bit accuracies are:

| arm | bit 1 | bit 2 | bit 3 | joint |
|---|---:|---:|---:|---:|
| LOCAL_REP | .7344 | .7240 | .7604 | .3802 |
| A0 | .6145 | .5460 | .5108 | .1526 |
| A1 | .7012 | .6563 | .5918 | .2598 |
| A2 | .7695 | .7715 | .7539 | .4180 |
| A3 | .9941 | 1.0000 | 1.0000 | .9941 |
| A4 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

`A1-A0` by environment seed was:

| seed | ΔPi = A1−A0 |
|---:|---:|
| 9201 | +.1797 |
| 9202 | +.1641 |
| 9203 | +.0534 |
| 9204 | +.0313 |

Thus the correspondence gain is positive in all four seeds, but reaches the
preregistered +0.10 per-seed criterion in only two. Aggregate A1 is .2598,
above the .25 auxiliary floor.

## Geometry-stratified result

`LOCAL_REP` is the only frozen same-family reference and is used as the diagonal
reference `D`; cross-domain arms supply `O` only where the manifest contains
true-SAME cross pairs.

| geometry | D (`LOCAL_REP`) | A0 cross O | A0 Q=D−O | A1 cross O | A2 cross O |
|---|---:|---:|---:|---:|---:|
| GLOBAL | .4375 | .1671 | .2704 | .2734 | .4401 |
| BLOCK | .3359 | .1094 | .2266 | .2188 | .3516 |
| DIAGONAL | .3672 | n/a | n/a | n/a | n/a |

The frozen task population deliberately contains no true-SAME cross pairs in
DIAGONAL. It therefore cannot estimate diagonal off-diagonal transfer, `R_DIAGONAL`,
or the preregistered GLOBAL/BLOCK/DIAGONAL Q ordering. Likewise, BLOCK contains
only within-block true-SAME pairs, so a within-vs-cross BLOCK contrast `B_BLOCK`
is not identified by these paid cells. These are protocol-identifiability limits,
not missing-data imputation opportunities; no calls were added.

## Bottleneck localization

The representation ladder provides the strongest evidence:

- `A0 -> A1 = +0.1071`: a visible semantic correspondence improves transfer,
  but does not restore reliable competence.
- `A1 -> A2 = +0.1582`: canonicalizing the history and target helps further.
- `A2 -> A3 = +0.5762`: an explicit policy table almost solves the task.
- `A3 -> A4 = +0.0059`: canonicalizing the target after the rule is explicit adds
  little.

This pattern is consistent with a **rule-induction / reusable-history
representation bottleneck**, not primarily a target semantic renderer failure.
It does not prove a unique mechanism: context interference, example anchoring,
joint-output composition, and pretrained semantic priors remain live alternatives.

## Source-success transport

The source-local response was joined by frozen latent probe suffix, because local
and cross rows intentionally use different family prefixes. Cross accuracy rose
with the local source response:

| arm | local source incorrect | local source correct |
|---|---:|---:|
| A0 | .0930 (n=301) | .2381 (n=210) |
| A1 | .1528 (n=301) | .4123 (n=211) |
| A2 | .2890 (n=301) | .6019 (n=211) |

This is a diagnostic association, not an independent causal estimate. The exact
source and target semantic cases differ, and each probe remains nested within an
environment seed.

## Anchoring and response diagnostics

Any-memory action-copy rates were high: A0 .865, A1 .848, A2 .813. Last-action
copy was .247, .156, and .207 respectively. Joint-output entropy was 2.819 bits
(A0), 2.910 (A1), and 2.930 (A2), so the response is not simply a single modal
output. Still, any-memory copying is a major confound for interpreting positive
transfer-like cells as policy induction.

## Qualification gates

The preregistered learner-geometry qualification is **not met**:

| gate | status | reason |
|---|---|---|
| A: GLOBAL diagonal learning | partial | LOCAL_REP=.4375 is positive, but no independent empty-memory subtraction was frozen in this ladder |
| B: BLOCK diagonal learning | partial | LOCAL_REP=.3359 is positive under the same caveat |
| C: DIAGONAL diagonal learning | partial | LOCAL_REP=.3672; cross counterpart absent |
| D: GLOBAL density `R_GLOBAL≥.50` | FAIL | A0 O/D ≈ .382 |
| E: BLOCK contrast `B≥.05` | NOT IDENTIFIABLE | no BLOCK cross-block true-SAME cells |
| F: DIAGONAL locality `R_DIAGONAL≤.50` | NOT IDENTIFIABLE | no DIAGONAL cross true-SAME cells |
| G: Q ordering | NOT IDENTIFIABLE | DIAGONAL Q unavailable; GLOBAL/BLOCK A0 ordering is opposite in the available cells |
| H: geometry alignment | PARTIAL | A1 and A2 improve, but full matrix gate cannot be evaluated for DIAGONAL |

The honest classification is **PARTIAL / NOT QUALIFIED**, not a pass and not a
claim that the model has no transfer capability.

## What this establishes

1. The frozen harness executed the intended ladder without technical loss.
2. DeepSeek can solve the semantic target nearly perfectly when the exact policy
   table is supplied (A3/A4).
3. The model receives a measurable benefit from explicit semantic correspondence
   and canonicalized histories.
4. The dominant remaining difficulty lies between natural resolved examples and
   an executable reusable policy.

## What this does not establish

- It does not establish spontaneous specialization, routing, or a social
  feedback mechanism.
- It does not establish that DeepSeek cannot learn the policy with another
  interface, more exposure, or another model.
- It does not identify a unique cognitive mechanism.
- It does not provide the missing BLOCK cross-block or DIAGONAL cross-domain
  contrasts.
- It does not turn `P L^T D_rho P` into an observed LLM-society Jacobian.

## Artifacts

Authoritative outputs are in
`reports/task-ecology/cross-domain-transfer-bottleneck-v1/`, including the
manifest, prompt audit, raw-derived response table, ladder, per-seed and
aggregate matrices, geometry metrics, transport/stratification tables,
anchoring, technical health, cost, and figures. The raw append-only journal is
`data/auto-research/cross-domain-transfer-bottleneck-v1/events.jsonl`.

No further paid inference or society experiment was run after completion.
