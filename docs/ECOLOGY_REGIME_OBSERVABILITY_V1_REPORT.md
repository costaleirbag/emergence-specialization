# Ecology Regime Observability V1 — report

## Executive result

**Status: COMPLETE — offline construct-validity audit.**

The principal diagnosis is confirmed. V2's exact Bayes oracle was conditioned on
the realized simulator geometry `G`, while DeepSeek's model-facing prompt did
not expose `G` or an equivalent sharing relation. This creates genuine
observational aliasing in the cross-domain comparison. The V2 harness is valid,
and its same-family plasticity result remains useful; the conditioned
cross-domain geometry should be reclassified as **CONFOUNDED BY REGIME
OBSERVABILITY**, not as a clean test of geometry recovery.

No external model calls, credential accesses, society runs, or V2 data changes
occurred in this audit.

## V2 source audit

`exact_bayes(task)` receives `geometry`, source family, target family, history,
and probe. It constructs a geometry-conditioned posterior. By contrast,
`SYSTEM_PROMPT`, `render_user`, and `OUTPUT_INSTRUCTION` render only the semantic
cases, resolved labels, and JSON schema. They contain no `GLOBAL`, `BLOCK`,
`DIAGONAL`, `SAME_POLICY`, or `INDEPENDENT_POLICY` token. The model therefore
does not observe the variable used by the old oracle.

## Prompt identity and aliasing

The frozen V2 manifest yields:

| quantity | value |
|---|---:|
| cross-domain triples | 384 |
| identical prompt across all three geometries | 96 |
| identical prompts with different hidden truth | 91 |
| fraction | **94.7917%** |

Pairwise identical-prompt counts are GLOBAL/BLOCK 192, GLOBAL/DIAGONAL 96, and
BLOCK/DIAGONAL 96. Different-truth counts among those are respectively 112, 78,
and 86. See [the aliasing audit](V2_GEOMETRY_PROMPT_ALIASING_AUDIT.md) for
representative cases.

If the same visible prompt `z` has truths `y_g != y_g'`, no function `f(z)` can
be correct for both regimes. This follows directly from the conflicting labels;
it is an identifiability theorem, not a claim about DeepSeek.

## Regime observability

Introduce `G ∈ {GLOBAL,BLOCK,DIAGONAL}` with experimenter meta-prior `1/3` each.
For a single source history, exact enumeration shows the source-history
marginal is identical under all three regimes. Therefore:

`P(G | H_source, X_target) = P(G) = (1/3,1/3,1/3)`

and `I(G; H_source, X_target)=0` in the frozen single-source protocol. This is
not an approximation and does not identify DeepSeek's unknown effective prior
`q_m(G)`.

Under the uniform meta-prior, policy-sharing probabilities are:

| pair | probability of SAME_POLICY |
|---|---:|
| same family | 1 |
| ACCESS↔RELEASE or INCIDENT↔PROVENANCE | 2/3 |
| other cross-family pair | 1/3 |

## Three exact normative oracles

The audit recomputes prompt-level Bayes quantities for:

1. **HIDDEN:** marginalize over `G` using `P(G)=1/3`;
2. **RELATION:** condition only on the pairwise `SAME_POLICY`/`INDEPENDENT_POLICY`
   relation;
3. **FULL:** condition on the realized `G`, reproducing the old V2 oracle.

The FULL oracle reproduces V2's `A*` and `p_true` exactly. In this finite ecology,
the RELATION oracle also reproduces the FULL transfer opportunity for each
source-target pair: relation is sufficient for the pairwise policy posterior.
The HIDDEN oracle cannot recover the conditioned geometry:

| oracle | D | O | Q |
|---|---:|---:|---:|
| HIDDEN / GLOBAL | 0.8594 | 0.3819 | 0.4774 |
| HIDDEN / BLOCK | 0.8594 | 0.3819 | 0.4774 |
| HIDDEN / DIAGONAL | 0.8594 | 0.3819 | 0.4774 |
| RELATION / GLOBAL | 0.8594 | 0.8594 | 0.0000 |
| RELATION / BLOCK | 0.8594 | 0.2865 | 0.5729 |
| RELATION / DIAGONAL | 0.8594 | 0.0000 | 0.8594 |
| FULL / GLOBAL | 0.8594 | 0.8594 | 0.0000 |
| FULL / BLOCK | 0.8594 | 0.2865 | 0.5729 |
| FULL / DIAGONAL | 0.8594 | 0.0000 | 0.8594 |

These are normative opportunities, not empirical model scores.

## DeepSeek result reclassified

The V2 same-family gains remain valid and do not require regime identification:

- GLOBAL `D=+0.2578`;
- BLOCK `D=+0.2188`;
- DIAGONAL `D=+0.1875`.

They support **same-family plasticity: SUPPORTED** under the corrected harness.

For cross-domain cells, the old comparison against `L*_full` was a comparison to
a privileged oracle. The DeepSeek matrices remain useful descriptive evidence
about its spontaneous cross-domain prior, but not a clean recovery test:

- GLOBAL off-diagonal transfer was negative on average;
- BLOCK within-block contrast was absent;
- DIAGONAL showed the clearest locality.

Classification:

| component | status |
|---|---|
| V2 harness validity | VALID |
| same-family plasticity | SUPPORTED |
| conditioned cross-domain geometry recovery | CONFOUNDED BY REGIME OBSERVABILITY |
| spontaneous cross-domain prior | weak/local, descriptive only |

The old `PARTIAL` learner label is retained for chronology, but it must not hide
these distinct claims.

## Baseline replication and stochasticity

There are 84 unique empty-memory prompt groups among 384 baseline rows. Pooling
all observed baseline responses for the same model-facing baseline prompt and
scoring each against its geometry-specific truth changes D/O but leaves Q
unchanged:

| geometry | original D | pooled D | original O | pooled O | Q (both) |
|---|---:|---:|---:|---:|---:|
| GLOBAL | 0.2578 | 0.2869 | −0.0495 | −0.0204 | 0.3073 |
| BLOCK | 0.2188 | 0.2305 | 0.0104 | 0.0221 | 0.2083 |
| DIAGONAL | 0.1875 | 0.2109 | −0.0339 | −0.0104 | 0.2214 |

Thus baseline response stochasticity changes marginal gain estimates but does not
explain the Q-ordering failure. Algebraically, for `L_cd=A_cd−B_d`, each target
baseline `B_d` appears once in the diagonal mean and `K−1` times in the balanced
off-diagonal mean, with equal total weight. The same cancellation holds for
BLOCK `W−C` when each target is represented equally in the two four-edge sets.

## Options for the next gate

### A — known ecology

Give the sharing structure to the learner. This is the cleanest positive control
for whether it can infer and apply a source policy, but it is more synthetic.

### B — hidden but inferable ecology

Expose multiple families and enough evidence that an agent can infer both task
policies and the regime. This is closer to developmental learning, but adds a
new latent belief state and a larger identifiability problem.

### C — hidden and unidentifiable ecology

Retain the current V2 setup as a study of the model's spontaneous prior `q_m(G)`.
This is a valid object, but it is not a clean test of conditioned ecological
geometry.

## Recommendation

The cheapest discriminating next gate is **RELATION-SIGNALED CROSS-DOMAIN
TRANSFER V1**, design only, not executed here. Reuse V2 histories, probes, model,
and natural h=8; add exactly one natural-language statement saying whether the
current source-target procedures share an underlying policy. Do not reveal the
policy or theta. This aligns the learner-visible information set with the
RELATION oracle and tests whether the missing structural prior, rather than
failure of rule induction, explains cross-domain transfer.

This recommendation is not a society authorization. A later hidden-but-inferable
study should remain the more natural developmental question if the positive
control succeeds.

## Society implication

If regime structure is endogenous, a future agent state should include a belief
`q_i(G,t)=P_i(G|experience up to t)` alongside competence and memory. Effective
transfer could then be represented conceptually as
`L_i(t)=Σ_g q_i(g,t)L_i(g,t)`. This is a future model, not an established
equation or an implemented society mechanism.

## Audit boundary

V2 remains preserved as a correctly preregistered historical experiment. This
audit refines the information hierarchy; it does not rewrite raw data or claim
that V2 was a failed experiment. No bottleneck ladder, additional learner call,
or society run was executed.
