# Theory V1 — derivation and assumptions

## Centering

`P_K` removes the niche mean because `P_K 1 = 0`. Applying it on both sides of
`Kᵀ D_rho` restricts the transfer calculation to niche contrasts: uniform
competence shifts are not specialization. The agent contrast is represented by
`P_N A P_K`; the per-agent linear perturbation is evaluated in the niche
contrast space.

## Router linearization

For `q_i(c)=exp(beta mu_ic)/Σ_j exp(beta mu_jc)`, at equal `mu` the derivative
with respect to an agent-centered perturbation is `beta/N`. Exploration mixes
this differential signal with a uniform draw, giving `(1-epsilon) beta/N`.

## Feedback and retention

The selected agent always receives feedback. An unselected agent receives it
with probability `q`, so its mean update probability is
`u(q)=q+(1-q)/N`. The frozen FIFO approximation retains
`r=1-u(q)/k` per effective step. This is a mean-field assumption, not a measured
law.

## Jacobian and spectra

Combining retained contrast with competence-sensitive allocation gives
`J=rI+(1-q)((1-epsilon)beta/N)T_k`. The exact discrete criterion is the spectrum
of this explicit matrix. The scalar `beta_c` is reported only when the dominant
real eigenvalue of `T_k` is positive and identifiable. `q=1` removes the
differential feedback term, so no finite beta threshold is forced.

Non-normality matters: a stable spectrum can still show transient amplification,
so numerical abscissa and singular/transient diagnostics are exploratory. A
dominant mode is only eligible under the preregistered spectral-gap rule.

## Assumptions and boundaries

- finite `N=K=4` and uniform `rho` are protocol choices;
- competence is treated as a local continuous response for the effective model;
- the measured `K` is not itself proof of social causality;
- `T_k` and `J` are model-derived objects, not direct LLM internals;
- late nonlinear saturation and team utility are outside the formation theorem.
