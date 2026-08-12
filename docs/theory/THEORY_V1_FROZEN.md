# Theory V1 — frozen developmental dynamics

**Status:** protocol specification; no prospective social result exists.

For `N=K=4`, each agent has held-out competence vector `a_i(t)` and the
population competence matrix is `A(t)`. The primary formation observable is the
double-centered interaction:

```text
P_N = I - 11ᵀ/N       P_K = I - 11ᵀ/K
Z(t) = P_N A(t) P_K
Psi_spec(t) = ||Z(t)||²_F / (N K)
```

`Psi_spec_bit` is primary; `Psi_spec_joint` is confirmatory. `Phi`, HSE,
matching gain, routing information, and team utility are secondary and cannot
replace `Psi_spec`.

Microscopic memory composition `n_i` is mapped locally by a measured operator
`K^(k)`, with source niches on rows and target competence niches on columns:
`delta a_i ≈ K^(k)ᵀ delta n_i`. The centered transfer operator is:

```text
T_k = P_K (K^(k))ᵀ D_rho P_K
```

The frozen effective linearization is:

```text
r(k,q) = 1 - [q + (1-q)/N] / k
J = r I + (1-q) ((1-epsilon) beta / N) T_k
```

`R_spec` is the spectral radius on the niche-centered subspace and
`lambda_spec = log(R_spec)`. `R_spec < 1` is subcritical/noise-maintained;
`R_spec > 1` is amplifying in the linearized effective model. This is not an
empirical claim that `J` is the Jacobian of an LLM society.

The prospective test uses exactly two ecology families, fresh micro/social seed
spaces, `k ∈ {4,8,12}`, the fixed 18-cell social grid, and no post-hoc additions.
