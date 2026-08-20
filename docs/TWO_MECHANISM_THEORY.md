# Two-mechanism theory: competence versus contextual anchoring

**Status:** minimal explanatory framework. It is not fitted to the LLM data and
does not replace HSE or the executed experiment.

## Why two latent states are needed

The original developmental loop was:

```text
experience -> niche competence -> confidence/allocation -> more experience
```

Clean v2 shows behavioral differentiation, but the single-agent calibrations do
not show reliable hidden-rule learning and confidence is weakly informative.
The minimal state description must therefore distinguish:

- competence `x_i,c(t)`: probability that agent `i` can solve world `c`;
- contextual anchor `q_i,l(t)`: propensity to emit answer label `l` because of
  visible memory, independent of correctness.

One qualitative response model is

$$
P(Y_i=l\mid c,M_i)
=(1-\lambda_i)P_F(l\mid c,x_i)
+\lambda_i\big[(1-\rho_i)q_{i,l}+\rho_i\,\mathbb{1}(l=L_i^{last})\big],
$$

where `P_F` is the competence-mediated response distribution and the second
term captures modal/frequency and last-item anchoring. This is a decomposition,
not an identified estimator.

## Model F — functional specialization

Experience in world `c` updates target competence:

$$
x_{i,c}(t+1)=x_{i,c}(t)+\eta\,u_{i,c}(t)
\big(1-x_{i,c}(t)\big),
$$

where `u` indicates informative exposure. A competence-correlated allocator
then creates a reinforcing loop. Its characteristic observables are:

- held-out target competence rises;
- correct feedback beats corrupted/unrelated feedback;
- coefficient recovery rises for identifiable contexts;
- competence matrix differentiation `Phi` rises;
- matching gain and routing alignment can rise;
- order of the same sufficient examples matters little once the rule is
  identified.

This model requires two empirical gates: experience must change competence, and
some allocation signal must correlate with it.

## Model A — anchoring-only null

Set competence learning to zero (`eta=0`). Memory feedback updates only an
answer-label distribution:

$$
q_i(t+1)=(1-\alpha)q_i(t)+\alpha e_{z_t}
$$

for each recipient, with optional extra weight on the latest item. Under shared
feedback, all agents receive the same update and their `q_i` states contract or
remain aligned. Under private feedback, recipients see different sampled label
histories and their `q_i` states can diverge.

Consequently, even with fixed competence:

- shared answer agreement can rise and HSE can fall;
- private HSE can remain higher because local label histories differ;
- correctness need not improve;
- Phi, matching, and routing alignment need not rise;
- systematically corrupted labels can redirect output bias rather than teach
  truth;
- order/recent labels can strongly affect answers.

This establishes a logical possibility: developmental behavioral diversity does
not require functional specialization. It does not establish that Model A is
the unique explanation of clean v2.

## Discriminating observables

| Observable | Functional specialization | Contextual anchoring |
|---|---|---|
| Held-out competence | rises by target world | weak/no systematic rise |
| Correct vs corrupted feedback | correct clearly better | labels may redirect bias similarly |
| Coefficient recovery | increases in rank-full contexts | remains weak/unstable |
| Memory-order sensitivity | comparatively low after identification | comparatively high |
| Last/modal-label matching | incidental | elevated beyond coverage-aware null |
| Phi / matching gain | can rise | need not rise |
| Confidence utility | may rise if calibrated | weak/context-driven |
| Shared answer agreement | not required | expected to rise |
| Private behavioral HSE | functional only if competence changes | can rise without competence |

## Current evidential mapping

- **Examples -> identifiable rule:** mathematically supported for nearly all
  `k=4` and all `k=8` calibration contexts; impossible at `k<3`.
- **Identifiable examples -> model induction:** weak under the frozen
  thinking-off prompts.
- **Inferred rule -> arithmetic execution:** not isolated before this autonomous
  session.
- **Experience -> held-out competence:** weak/not demonstrated.
- **Competence -> confidence:** weak in the existing protocol.
- **Memory -> common response distribution:** observed association, not yet a
  causal order/content test.

## Important confounds in clean v2

The private/shared manipulation does more than share content. Shared agents have
equal, usually full eight-item memories, while private agents have fewer and
older/heterogeneous items. Thus common context, memory volume, age, label-set
coverage, and information locality are bundled. A future causal design must
match these factors or manipulate them factorially.

Likewise, any-label matching must be compared to a null based on how many labels
are visible and on the model's answer marginal. With five or six distinct labels
in an eight-item memory, high any-label overlap can occur without direct copying.

## Highest-information microscopic sequence

The least-confounded chain is:

1. certify rank and modularly disjoint probes offline;
2. give the correct rule explicitly and measure arithmetic execution;
3. give rank-full examples, request coefficients once, and score them offline;
4. if induction is nontrivial, reverse/shuffle the exact same memory multiset;
5. return to a society only if competence acquisition and an allocation signal
   become measurable.

