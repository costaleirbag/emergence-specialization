# Task ecology and transfer geometry

**Status:** construct-validity analysis and candidate design. No new ecology has
been executed or authorized by this document.

## The concern

All four current worlds instantiate the same operation class:

$$
z=ax+by+c\pmod 7.
$$

They differ in coefficients, not in the kind of procedure. This is an excellent
mechanistic setting for exact algebra, rank, controlled feedback, and behavioral
measurement. It is a narrower substrate for the broad construct “different
functional roles”. A hypothetical ALPHA/BETA split could mean:

- true world-specific coefficient knowledge;
- reuse of congruent examples;
- different contextual label anchors;
- one general modular-inference skill with different parameters.

Only the first is niche competence, and even that is **parameter
specialization inside one skill family**, not evidence/audit versus diagnosis/
planning-style procedural specialization.

This is a serious construct-validity threat, but not proof that GF(7) is
structurally incapable of specialization. If examples from world `c` produced a
reproducible advantage on unseen `c` tasks but not on `d`, the ecology would have
a diagonal transfer geometry and support a narrow, controlled form of niche
specialization. Existing non-alias calibration evidence does not show that
channel.

## Directed learning-transfer matrix

Let `c` be the exposure family and `d` the evaluation family. With matched
initial agent copies, forced exposure, and a no-feedback/placebo control, define

$$
L_{cd}(h)=
\mathbb E\left[A_d^{post}(h)-A_d^{pre}\mid E_c\right]
-
\mathbb E\left[A_d^{post}(h)-A_d^{pre}\mid E_0\right].
$$

`h` is the delay after exposure. It distinguishes transient prompt priming from
retained procedural competence. A simpler post-minus-baseline estimator is
acceptable only when matched clones make the pretest unnecessary and leakage is
controlled.

Useful summaries, reported only alongside the full directed matrix, include:

$$
D=\frac1K\sum_cL_{cc}
$$

(diagonal learnability),

$$
Q=\frac1K\sum_c\left(L_{cc}-\frac1{K-1}\sum_{d\ne c}L_{cd}\right)
$$

(within-source locality/comparative advantage), and

$$
S=\frac{1}{K(K-1)}\sum_{c\ne d}|L_{cd}-L_{dc}|
$$

(directed transfer asymmetry). Negative off-diagonal entries measure
interference/forgetting. Block-diagonal structure may be more meaningful than a
strict diagonal when niches share subskills.

Two ecology failure modes are immediate:

- `L approximately 0`: experience teaches nothing reusable;
- rows/columns are nearly flat and positive: experience transfers everywhere,
  favoring generalists rather than comparative advantage.

A strongly diagonal matrix is not sufficient for society-level specialization.
It only makes specialization possible. Allocation, persistence, capacity, and
collective utility remain separate gates.

## How to estimate L without routing confounds

Estimate ecology first with single-agent matched copies and **forced randomized
exposure**, before endogenous routing:

1. choose source exposure `c` or matched placebo/no-feedback;
2. match token count, example count, prompt length, and order;
3. probe every target family `d` on untouched generated items;
4. use independent context seeds as replication units;
5. evaluate immediately and after one or more intervening blocks;
6. counterbalance exposure order or use fresh copies;
7. score the full matrix, not only diagonal cells.

Item overlap must be excluded at the level of latent templates, entities,
simulator seeds, and procedures—not merely exact surface strings. A hierarchical
binomial/logistic analysis can include context/agent and item effects, baseline
ability, prompt length, and order. Raw response count is not the independent
sample size.

## Properties of a specialization-capable ecology

A candidate ecology should have:

- measurable learning at the available memory/horizon;
- procedural distinctions, not just renamed domains;
- nontrivial directed transfer or interference;
- opportunity for comparative advantage rather than one universally best
  procedure;
- matched baseline difficulty and answer priors;
- a binding capacity/allocation constraint;
- repeated demand and retained competence;
- generated contamination-resistant tasks;
- exact or high-agreement objective verifiers;
- family labels counterbalanced or latent to model/router while retained for
  experimenter-side scoring.

Maximum heterogeneity is not automatically best. Completely unrelated tasks can
produce isolated memorization with no shared economy. The scientifically useful
regime likely contains reusable subskills plus niche-specific operations.

## Candidate semantic/procedural ecology

The strongest current design is a generated **procedural microservice ecology**
with a common small JSON/multiple-choice response schema but different exact
interpreters:

1. **Grounded command execution:** interpret nonce modifiers and compose actions
   in a grid state; verifier executes the action sequence or checks final state.
2. **Relational inference:** compose inverse/symmetric/transitive/tree-path
   relations over nonce entities; verifier solves the generated graph.
3. **Workflow diagnosis:** infer a root failure from finite-state transition and
   sensor traces under a run-specific codebook; verifier owns the simulator.
4. **Constraint/provenance audit:** identify the violated integrity or precedence
   rule in a generated record graph; verifier evaluates exact constraints.

Family identity should normally be experimenter-side. Tasks may have distinct
surface structure, but should not carry easy `ALPHA`-style labels that hand the
router a niche ID. The model must infer the relevant procedure from task
content. For initial calibration, explicit family labels can be a separate
observability positive control, not the default.

Free-form creativity is intentionally excluded: it makes `L` hard to score and
invites evaluator-model confounds.

## Literature connection

- Taskonomy treats relations among tasks as measurable directed transfer rather
  than semantic intuition, motivating `L`: https://arxiv.org/abs/1804.08328
- gSCAN supplies grounded generated commands, exact world-state semantics, and
  compositional splits: https://papers.nips.cc/paper_files/paper/2020/hash/e5a90182cc81e12ab5e72d66e0b46fe3-Abstract.html
- CLUTRR supplies generated relational stories, held-out logical combinations,
  and exact relation labels: https://arxiv.org/abs/1908.06177
- Continual-learning theory emphasizes that transfer/forgetting depends on task
  relations rather than task names: https://proceedings.mlr.press/v139/lee21e.html
- ROMA produces specialized roles through explicit role machinery in MARL,
  illustrating that behavior diversity and functional role are separate:
  https://proceedings.mlr.press/v119/wang20f.html
- EVOCHAMBER (2026 preprint) already reports stable niche specialists from
  identical initial agents on heterogeneous streams. That makes “spontaneous
  roles exist” alone a weak novelty claim: https://arxiv.org/abs/2605.11136

The possible contribution is sharper: **measure transfer geometry before the
society run and test whether its topology predicts role formation, routing
alignment, retention, and collective gain.** This is a hypothesis requiring a
dedicated literature review before any novelty claim.

## Adversarial critique of the reframing

The reframing can fail in several ways:

- a diagonal `L` may be engineered by arbitrary nonce mappings and still lack
  meaningful function;
- semantic families introduce unequal difficulty, prompt length, scoring noise,
  pretraining knowledge, and latency/cost;
- making family identity latent can turn a competence test into a task-
  recognition test;
- making it explicit makes routing trivial;
- objective generators can still contain shortcuts;
- selecting an ecology after seeing favorable transfer is adaptive benchmark
  construction;
- task-transfer structure alone does not explain which agent gets which role.

Therefore candidate ecologies must be preregistered, include placebo and
cross-family exposure, preserve negative results, and be selected by explicit
construct criteria—not by which one produces the prettiest specialization.

## Current decision

GF(7) should remain as:

- an exact mechanistic control;
- an identifiability and execution diagnostic;
- a likely low-learnability/null ecology;
- evidence that behavioral differentiation can occur without demonstrated
  functional competence.

It should not remain the sole basis for a broad functional-specialization claim.
The next ecology work should be offline: specify generators/verifiers and test
their invariants locally. Only then run a tiny single-agent transfer pilot.

### Cheapest semantic-ecology pilot after offline validation

Use a sequential falsification design rather than paying for the full matrix at
once. A two-family screen with source exposure `{none,c1,c2}`, two independent
context seeds, both target families, four untouched probes, and one response per
prompt costs:

$$
3\times2\times2\times4=48
$$

logical calls. This is only a coarse screening matrix: it can reject a candidate
with no diagonal learning or obviously flat transfer, but cannot establish a
stable ecology. Freeze the full design before inspecting these calls. If the
screen passes its preregistered gate, add families, seeds, and exact-prompt
replicates. For example, a gross three-family follow-up with source exposure
`{none,c1,c2,c3}`, two context seeds, all targets, four probes, and two
replicates costs:

$$
4\times2\times3\times4\times2=192
$$

logical calls in total. Even that would be descriptive rather than powered
inference. A cost cap must be based on finalized prompt sizes. Neither stage is
implemented, preregistered, or authorized for execution.
