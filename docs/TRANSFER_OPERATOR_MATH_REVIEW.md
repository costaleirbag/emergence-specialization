# Transfer operator: derivation and red-team review

This note is a mathematical audit of the explicit effective model. It is not an
empirical claim about an LLM society.

## Orientation and projection

Rows of `L` index the source niche and columns index the target niche. If
`e_i` is a source-experience rate vector, the target competence gain is
`L.T @ e_i`; this is why the transpose is present. The target contrast
projection is applied on the left. On the restricted state space
`1.T a_i = 0`, the input perturbation is already in the range of `P`, so the
restricted operator is

`T(L) = P L.T D_rho P`.

The right-hand `P` is therefore a state-space restriction, not an assertion
that source frequencies are themselves contrast-free. Without that restriction
the full derivative contains `P L.T D_rho` and has additional generalist/mean
directions.

## Softmax linearization

At the exchangeable state, all agents have the same competence vector and
`p_i(c)=1/N`. For a fixed niche `c`,

`d p_i(c) = beta p_i(c) (d a_i,c - sum_j p_j(c) d a_j,c)`.

Thus

`d p_i(c) = (beta/N)(d a_i,c - (1/N) sum_j d a_j,c)`.

For an across-agent zero-sum perturbation, the second term vanishes and the
frozen derivation `d p_i(c) = beta d a_i,c/N` follows. This is a condition on
the perturbation sector, not a statement about arbitrary perturbations.

## Full finite-N Jacobian

Let `B=(eta beta/N) P L.T D_rho`. For agent blocks `i,j`, the full Jacobian at
exchangeability is

`J_ii = (1-1/N)B - gamma I`,

`J_ij = -B/N` for `i != j`.

The population-mean sector has Jacobian `-gamma I`; the `(N-1)` independent
zero-sum agent sectors each have

`B - gamma I`.

Restricting those sectors further to niche contrasts gives

`J_specialization = (eta beta/N) T(L) - gamma I`.

Consequently the explicit model has an instability in that sector iff the
largest real eigenvalue of `T(L)` exceeds `N gamma/(eta beta)`. This is a
linear asymptotic statement. It is not sufficient to infer nonlinear role
formation.

## Mean competence and relaxation

The left projection removes the uniform target direction from each learning
increment, but it does not generally conserve the population mean competence:
`P L.T rho` need not be zero. The `-gamma a_i` term is an explicit relaxation
assumption. Neither property is asserted to hold in the LLM implementation.

## Symmetry

The permutation group `S_N` acts by permuting agent rows. With identical initial
states and an agent-label-free update rule, the effective dynamics are
permutation-equivariant. The exchangeable subspace is fixed by `S_N`; its
orthogonal complement is the zero-sum agent sector. A single stochastic finite-N
trajectory can leave the fixed subspace, producing a within-run asymmetry, while
the ensemble distribution remains label-exchangeable. This is the appropriate
finite-population signature of spontaneous differentiation, not a thermodynamic
phase-transition claim.

## Asymmetric and non-normal transfer

For directional transfer, `T` need not be symmetric. The largest real eigenvalue
controls eventual exponential growth/decay of an eigenmode, but non-normal `T`
can produce transient amplification even when every eigenvalue is stable. The
offline report therefore separates:

- eigenvalue susceptibility `max Re eig(T)`;
- symmetric-part numerical abscissa `lambda_max((T+T.T)/2)`;
- finite-time `||expm(T t)||_2` over a declared dimensionless grid;
- eigenvector conditioning when the eigendecomposition is numerically stable.

Transient growth is not persistent specialization and must not be described as
such.

## Ideal limits

For `L=alpha 11.T`, `P L.T P=0`, so the contrast susceptibility is zero. For
`L=qI`, the `K-1` contrast modes are degenerate with `T` eigenvalue `q/K` under
uniform frequencies. For the symmetric block matrix with `d>w>c`, the block
mode has eigenvalue `d+w-2c`, while the two within-block modes have `d-w`.
After uniform-frequency scaling, the block mode dominates exactly when
`d+w-2c > d-w`, equivalently `w>c`. The inequalities also ensure that diagonal
within-niche retention exceeds cross-block transfer in the intended qualitative
geometry.

## Boundary of interpretation

1. **Empirical fact:** the frozen run measures `L` and response-level accuracy.
2. **Mathematical fact:** `T(L)`, eigenvalues, singular values, and Rayleigh
   quotients are deterministic functions of measured `L`.
3. **Model result:** the effective dynamics have the stability condition above.
4. **Future hypothesis:** a real adaptive LLM society will approximately follow
   those contrast modes.

The fourth statement is explicitly untested until a separate society protocol.
