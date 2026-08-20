# Ecological information geometry

This document defines the offline construct-validity layer used before any
future LLM experiment. It is deliberately an ecology-level result, not a claim
about an LLM.

For a geometry `g`, let the hidden ecology parameter be `Theta ~ p_g`. A case
family `c` has symbolic input `X_c` and deterministic output
`Y_c = V_c(X_c, Theta)`. A natural history of length `h` is
`H_c^(h) = ((X,Y)_1, ..., (X,Y)_h)`, sampled IID from the frozen case
generator. The information available for transfer from family `c` to `d` is

    J_cd(h) = I(Y_d ; H_c^(h) | X_d)

measured in bits. Equivalently, `J = H(Y_d|X_d) - H(Y_d|X_d,H_c)`. The
normalized value divides by `log2(|Y_d|)`. V3 has three independent binary
components, so the denominator is 3 bits and `|Y| = 8`.

The decision-theoretic counterpart is Bayes accuracy under the stated ecology
prior:

    A*_cd(h) = E[max_y p(Y_d=y | X_d,H_c)]
    L*_cd(h) = A*_cd(h) - A*_cd(0)

`J` is predictive information; `L*` is task-specific 0-1 decision utility.
Neither is a universal upper bound on a pretrained model: both depend on the
specified prior, representation, sampling process, verifier, and loss.

## Hierarchy

The intended causal hierarchy is:

    G -> J -> L* -> L_model -> T(L)

`G` is designed latent sharing. `J` checks whether that sharing is predictive
in the observable ecology. `L*` asks what an ideal learner could exploit. A
future model transfer matrix and social operator are later, separate empirical
layers.

## Propositions

* Independent source and target latent variables imply `J_cd(h)=0` under the
  stated prior.
* Conditioning on a nested history cannot decrease mutual information.
* In a block prior, cross-block `J` is zero while within-block `J` can be
  positive.
* A shared latent parameter gives non-zero cross-niche information unless the
  verifier discards it.

These are probability statements. A finite Monte Carlo estimate can deviate
from zero; independent cells are also checked analytically in the V3 code.

## V3 ecology

Each family (ACCESS, RELEASE, INCIDENT, PROVENANCE) presents three natural
policy signals, each taking values 0--3. Each hidden component is one of the six
balanced Boolean maps from four values to two values. The output is the three
bits jointly. There is no short-circuit rule and no family/geometry/theta token
in the rendered case. GLOBAL shares one three-map vector, BLOCK shares one
vector within each pre-registered pair, and DIAGONAL draws one vector per
family. All 64 symbolic cases are valid and IID natural histories allow repeats.

The design is intentionally synthetic and auditable. Passing its gates means
only that the ecology contains a known information-transfer opportunity; it does
not establish semantic realism, model learnability, or specialization.

## Caveats

The exact Bayes learner uses a uniform prior over the six balanced maps. This is
not a claim about a pretrained model's prior. Natural and teaching histories
are separate estimands. Information is conditional on `X_d`, and history order
is retained in the serialized sequence even though the exact Bayes posterior is
exchangeable here.

## V3.1 observation correction

V3.1 separates the latent symbolic state from what reaches a learner:

    U=(C,X) -> O=psi(C,X) -> Z=phi(O)

`O` is a structured semantic representation; `Z` is deterministic natural
language. The observable history is `Htilde_c^(h)=((O,Y)_1,...,(O,Y)_h)` and

    J_obs,cd(h) = I(Y_d ; Htilde_c^(h) | O_d).

The former V3 quantity is explicitly named `J_latent`: its oracle receives exact
source/target family and symbolic task state. If `psi` is injective for the
task-relevant `(C,X)`, observable and latent conditioning are equivalent and
`J_obs=J_latent` under the exact model. This is a conditional data-processing
statement, not a generic claim about arbitrary text strings.

The full hierarchy is:

    G -> J_latent -> psi -> J_obs -> L*_obs -> L^m -> T(L^m) -> A(t).

An LLM may fail at the `Z -> O` step even when the deterministic renderer is
semantics-preserving. That learner-dependent gap is the subject of a future,
small calibration—not of V3.1 itself.
