# V2 geometry prompt-aliasing audit

## Result

The frozen V2 manifest contains 384 cross-domain comparison triples: each fixes
seed, source family, target family, and symbolic target input while varying the
hidden geometry. In **96** triples, the three model-facing prompt hashes are
identical. In **91/96 = 94.7917%**, the correct target output differs across at
least two hidden geometries.

Pairwise counts (384 comparisons per pair) are:

| pair | identical prompt | different truth among identical |
|---|---:|---:|
| GLOBAL / BLOCK | 192 | 112 |
| GLOBAL / DIAGONAL | 96 | 78 |
| BLOCK / DIAGONAL | 96 | 86 |

The cross-domain triples include 32 canonical block-pair aliases and 64 other
cross-family aliases among the 96 all-geometry aliases. The aggregate counts are
computed from the frozen prompt hashes and target labels, not from DeepSeek
responses.

## Representative aliases

The prompt hash is shown only as an audit identifier; the prompt text itself is
not reproduced unnecessarily.

| seed | source → target | X | shared prompt hash (prefix) | GLOBAL | BLOCK | DIAGONAL |
|---:|---|---|---|---|---|---|
| 9201 | ACCESS → RELEASE | [0,0,0] | `fe78f02f` | [0,0,0] | [0,0,0] | [1,0,1] |
| 9201 | ACCESS → RELEASE | [0,0,3] | `38ae8cf7` | [0,0,1] | [0,0,1] | [1,0,0] |
| 9201 | ACCESS → RELEASE | [1,1,1] | `b8994ef5` | [1,1,1] | [1,1,1] | [1,1,0] |
| 9201 | ACCESS → RELEASE | [1,1,2] | `c1943a97` | [1,1,0] | [1,1,0] | [1,1,1] |
| 9201 | ACCESS → RELEASE | [2,2,2] | `7a369eed` | [1,0,0] | [1,0,0] | [0,1,1] |

These are observational aliases: the learner-visible input is unchanged while
the simulator's hidden regime changes the truth. They do not show that DeepSeek
made an error; they show that a geometry-conditioned oracle has privileged
information relative to the prompt.

## Formal consequence

For an identical visible prompt `z` with truths `y_g != y_{g'}`, a deterministic
rule `f(z)` cannot return both values. Choosing `y_g` fails under `g'`, choosing
`y_{g'}` fails under `g`, and any third output fails under both. Thus no rule on
the visible prompt alone is simultaneously Bayes-optimal for all conditioned
regimes. The correct normative comparison must specify whether `G` is hidden,
pairwise-relation-signaled, or fully observed.
