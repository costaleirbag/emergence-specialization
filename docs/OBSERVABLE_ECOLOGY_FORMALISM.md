# Observable ecology formalism

The latent task state is `U=(C,X)`, where `C` is a family/niche and `X` is the
three-dimensional symbolic input. An environment parameter is sampled as
`Theta ~ p_g(Theta)` and the verifier produces

    Y = V(C, X, Theta).

The learner does not have to observe `U` directly. Define a structured semantic
observation

    O = psi(C, X)

and a deterministic natural-language realization

    Z = phi(O).

The learner-facing resolved history is

    Htilde_c^(h) = ((O_c^1,Y_c^1), ..., (O_c^h,Y_c^h)).

The observable information geometry is

    J_obs,cd(h) = I(Y_d ; Htilde_c^(h) | O_d),

using base-2 logs. The latent reference is the previous V3 object

    J_latent,cd(h) = I(Y_d ; H_c^(h) | X_d),

where exact family identities are supplied to the oracle. The corresponding
Bayes gains are `L*_obs=A*_obs(h)-A*_obs(0)` and
`L*_latent=A*_latent(h)-A*_latent(0)`.

## Observation map and information loss

If `psi` is injective with respect to the task-relevant variables `(C,X)`, then
conditioning on `O` is equivalent to conditioning on `(C,X)` for this exact
generative model. Consequently `J_obs=J_latent` and `L*_obs=L*_latent`, up to
Monte Carlo error. Injectivity of unrelated metadata is unnecessary.

If `psi` is a deterministic lossy map, a data-processing statement applies only
to the variables in the specified Markov chain. In particular, when `O` is a
function of `(C,X)` and the target output is generated from the corresponding
latent state, the learner cannot recover information discarded by `psi`; one
must not quote a generic DPI inequality without preserving the conditioning on
the target observation.

The V3.1 semantic channel uses domain-identifying operational context and three
semantic attribute values. The host can deterministically decode `C_hat(O)` and
replay canonical `X` for the exact audit. This is an observation-model claim,
not a claim that a pretrained LLM will parse the English reliably.

## Hierarchy and physical analogy

The research hierarchy is

    G -> J_latent -> psi -> J_obs -> L^m -> T(L^m) -> A(t).

`G` is latent ecological coupling, `psi` is a measurement map, `L^m` is learner
response/susceptibility, and `T` is the later social feedback operator. The
analogy to measurement and response is useful, but it is not an equivalence to
a physical theory. Future work may make `psi` stochastic through ambiguity,
partial observability, noisy rendering, or lossy memory summaries.

Even an injective semantic `O` and deterministic `phi` do not establish that an
LLM extracts `O` from `Z`. The next paid gate must measure that separate
`q_m(O|Z)` realization layer.
