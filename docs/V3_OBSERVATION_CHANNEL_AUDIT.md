# V3 observation-channel audit

This audit records the old behavior before implementing V3.1.

## A. Symbolic variables

The V3 generator has `C` (family: ACCESS, RELEASE, INCIDENT, PROVENANCE),
`X=(x1,x2,x3)` with each component in `{0,1,2,3}`, hidden `Theta` containing
three balanced Boolean maps, and `Y=(y1,y2,y3)` produced by the verifier.

## B. Variables passed to the old exact Bayes learner

`posterior_predictive(environment, source, target, history, x)` received the
exact source family, exact target family, symbolic history, symbolic `x`, and
the geometry/environment object. The source and target IDs were therefore
privileged inputs to the old oracle.

## C. Variables rendered to a future LLM

The old `render_case` emitted only a generic sentence about three policy
signals and their numeric levels. It omitted the family entirely, and the
previous V3 report's natural-language renderer had no family-specific domain
context. The exact model-facing surface therefore contained `X`-like values but
not `C`.

## D. Did the old renderer preserve C?

No. It was family-blind.

## E. Did it preserve X injectively?

For the old generic renderer, the three numeric levels were recoverable in the
intended template, but family identity was not. Thus it did not preserve the
full task state `(C,X)`.

## F. Could the future learner know which niche policy applies?

Not from that surface. A model could only guess or use an external prior. The
old exact oracle, however, was told both source and target family.

## G. Classification

**PRIVILEGED-ORACLE MISMATCH.** The old `J_latent` result is mathematically
valid for its stated symbolic experiment, but it was not yet an analysis of the
observation channel available to a future LLM.

## Additional V3 bugs found

1. The previous component gate aggregated the three output-bit accuracies into
   one mean and did not store component 1/2/3 separately.
2. The previous Monte Carlo RNG included `h`, so h=1,2,4,8 used independent
   histories rather than prefixes of one h=8 draw. Marginal curves remain
   meaningful; paired developmental differences were not.

V3.1 corrects both in a new versioned analysis without changing the latent V3
prior or overwriting V3 files.
