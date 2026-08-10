# Learner-response geometry V2

## Scope

This note treats DeepSeek as a map from an observable ecology to realized
plasticity:

`E = (J_obs, L*_obs)  ->  L^m = M_m(E)`.

`M_m` is a descriptive learner map, not assumed linear, and this pilot does not
identify the model's pretrained prior `q_m(theta)`. The society operator
`T(L^m)` is a later effective-model object; it was not measured here.

## Evidence from the corrected V2 interface

The exact ecological opportunity was strong and known in advance: informative
prompt-level Bayes accuracy averaged 0.984375 in each geometry, while
independent cells were exactly 0.125. DeepSeek produced positive aggregate
diagonal gains in GLOBAL (0.2578), BLOCK (0.2188), and DIAGONAL (0.1875), so
some experience-dependent competence is measurable after eight natural resolved
cases.

The map did not preserve all of the designed geometry. GLOBAL expected dense
cross-niche opportunity but realized negative mean off-diagonal transfer
(`O=-0.0495`). BLOCK expected within-block advantage but realized `W=0` and
`B=-0.0156`. DIAGONAL had the clearest locality pattern (`D=0.1875`,
`O=-0.0339`). Alignment with exact `L*_obs` was positive and strongest for
DIAGONAL (raw 0.8031; centered 0.9322), but this is a four-seed, 16-cell
descriptive comparison.

## Decomposition

For each geometry, the report uses the identity

`L^m = alpha L*_obs + R`,

where `alpha` is a Frobenius projection coefficient and `R` is the residual.
This decomposition is not a causal variance partition. In V2, raw and centered
alignment are reported in `geometry_alignment.csv`; the residual should be
interpreted as model-specific response structure, including priors, semantic
analogy, context effects, and noise.

Positive transfer in zero-information cells is **learner-induced/prior-induced
transfer**, not ecological transfer. It is a key reason to compare `Q`, BLOCK
within-vs-cross contrasts, and exact `L*` rather than treating any gain as
evidence of niche learning.

## Response-level caveat

The neutral schema removed the V1 concrete-vector leak: the baseline modal output
was `[1,1,1]` in 49.0% rather than `[0,1,0]` in 61.1%, and transfer modal fraction
fell to 17.5%. Nonetheless baseline bit-one rates remain asymmetric and any-memory
action copying occurs in roughly 84–85% of transfer rows. Those facts are
diagnostics for model response behavior, not evidence that the model inferred a
latent family rule.

## Interpretation boundary

The measured result supports the narrow statement: **under the corrected
observable interface, DeepSeek exhibits small and heterogeneous natural
experience gains, with a clearer locality signal in DIAGONAL than in GLOBAL or
BLOCK.** It does not support the stronger statement that the model realizes the
ecology's intended transfer geometry, nor that a society would amplify it into
functional specialization.

The next allowed work is a principal-researcher decision about a cheap,
mechanistic single-agent diagnostic. A society experiment remains locked until a
learner geometry is explicitly qualified in a new reviewed protocol.

## Regime-observability correction

The V2 cross-domain comparison used a FULL-regime Bayes reference: its exact
oracle knew the simulator's `GLOBAL/BLOCK/DIAGONAL` value. The DeepSeek prompt
did not. Offline replay finds 96 identical cross-domain prompt triples and 91
with different truths, so a visible-prompt decision rule cannot be Bayes-optimal
for all conditioned regimes simultaneously.

The corrected hierarchy is therefore:

`p(G) -> G -> Theta -> H -> R -> q_m(G,Theta | H,R) -> L^m`.

The V2 diagonal gains remain evidence of same-family plasticity because same-family
sharing is true under every regime. Cross-domain values should instead be read as
descriptive evidence about DeepSeek's spontaneous structural prior, not as a clean
test of whether it recovered the conditioned ecology geometry. A relation-signaled
positive-control design is proposed, but not run.
