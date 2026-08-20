# Ecology regime observability formalism

## Ecology regime `G`

The simulator first samples a meta-ecology regime

`G ∈ {GLOBAL, BLOCK, DIAGONAL}`

with experimenter prior `P(G=g)=1/3`. It then samples latent policy parameters

`Theta ~ p(Theta | G)`.

The four semantic families and their hidden policies generate outputs
`Y_d = V(X_d, Theta_d)`. `G` exists in the generator; existence does not imply
that an agent observes it.

## Learner observation

The model-facing V2 prompt contains a semantic source history
`H_c = ((Z_c^r,Y_c^r))_{r=1}^8` and a semantic target case `Z_d`. It does not
contain a geometry name or a direct sharing flag. The semantic renderer is not
the same thing as an oracle receiving `G`.

## Regime observation variable `R`

We distinguish three normative information channels:

- **HIDDEN:** `R=null`; only the experimenter meta-prior over `G` is used.
- **RELATION:** `R∈{SAME_POLICY, INDEPENDENT_POLICY}` for the current source-target
  pair; no policy values or geometry name are supplied.
- **FULL:** `R=G`; the exact realized regime is supplied.

The actual V2 DeepSeek prompt is HIDDEN with respect to `G/R` for cross-domain
transfer. The RELATION and FULL channels are offline counterfactual oracles,
not additional model runs.

## Conditioned information geometry

The previous V2 reference is correctly named

`J_cond,cd(h;g) = I(Y_d ; H_c^(h) | X_d, G=g)`

and its decision value is

`L*_cond,cd(h;g) = A*_cond,cd(h;g) − A*_cond,d(0;g)`.

It answers: what can an ideal learner exploit if the ecology regime is known?
It must not be presented as information available to an agent that receives no
regime signal.

For a specified learner-visible channel `R`, define

`J_R,cd(h) = I(Y_d ; H_c^(h) | X_d, R)`

and

`A*_R,cd(h)=E[max_y p(Y_d=y | X_d,H_c^(h),R)]`,
`L*_R=A*_R(h)-A*_R(0)`.

## Hidden-regime Bayes learner

For the single-source V2 protocol, the source-history likelihood is identical
under all three regimes: the source family always receives one uniformly drawn
balanced policy, and its semantic X stream is condition-independent. Therefore

`P(G | H_c, X_d)=P(G)=1/3`.

The hidden oracle is

`p(Y_d | X_d,H_c,R=null) = Σ_g p(Y_d | X_d,H_c,G=g) P(G=g | H_c)`.

This is a normative experimenter-prior oracle, not a model of DeepSeek's unknown
pretrained prior `q_m(G)`.

## Relation-aware Bayes learner

The relation oracle conditions the same mixture on whether the current pair
shares a policy. Under the uniform meta-prior:

- same family: sharing probability `1`;
- canonical pairs ACCESS↔RELEASE and INCIDENT↔PROVENANCE: sharing probability
  `2/3` (GLOBAL or BLOCK);
- all other cross-family pairs: sharing probability `1/3` (GLOBAL only).

For this finite ecology, the pairwise relation is sufficient to reproduce the
full-regime Bayes opportunity for the corresponding source-target pair, even
though it does not reveal policy values.

## Full-regime oracle

The FULL oracle receives the exact realized `G`. Its prompt-level posterior
reproduces the previous V2 `exact_bayes` values exactly. This is a regression
check, not a claim about the DeepSeek prompt.

## Observational aliasing

If two geometries produce the same model-visible prompt `z` but different correct
outputs `y_g != y_{g'}`, then no deterministic decision rule `f(z)` can be
correct for both. If `f(z)=y_g`, it is wrong under `g'`; if it chooses `y_{g'}`,
it is wrong under `g`; and if it chooses another value it is wrong under both.
Randomization cannot be simultaneously Bayes-optimal for both either unless the
posterior assigns zero mass to one regime or the loss is changed. This is an
identifiability fact, not a model failure.

## Unknown learner prior `q_m`

DeepSeek may possess an effective semantic prior `q_m(G,Theta | H,R)` that is
not the experimenter-uniform prior. V2 behavior can be described relative to
simple hypotheses (local, global, block), but it cannot identify `q_m(G)` from
four seeds and one completion per prompt.

## Implications

V2 same-family gains remain interpretable because same-family policy sharing is
true under every `G`; they do not require the learner to identify `G`. The
cross-domain matrices are instead a mixture of ecological opportunity and an
unobserved-regime identification problem. Future work must explicitly choose:

1. known ecology (clean positive control);
2. hidden but inferable ecology (joint regime and policy learning); or
3. hidden and intentionally unidentifiable ecology (study the learner prior).

None of these options is executed by this audit.
