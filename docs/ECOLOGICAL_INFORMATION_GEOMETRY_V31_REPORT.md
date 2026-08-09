# Observable Ecological Information Geometry V3.1 report

## Executive result

V3.1 addresses a real construct mismatch in V3. The old Bayes oracle received
explicit source and target family IDs while the old renderer omitted family
identity. V3.1 adds a semantic observation channel, evaluates a learner whose
public interface receives only observable histories and target observations,
and retains a genuinely family-blind control. No external model calls were
made.

The machine-readable result is in
`reports/task-ecology/ecological-information-v31/`. The exact gate statuses are
in `gate_summary.json`.

All O1--O10 gates pass. Natural h=8 observable `J_normalized` summaries are:

| geometry | diagonal D | off-diagonal O | Q_J | Q_L* |
|---|---:|---:|---:|---:|
| GLOBAL | 0.99214 | 0.99214 | 0.00000 | 0.00000 |
| BLOCK | 0.99222 | 0.33074 | 0.66148 | 0.57558 |
| DIAGONAL | 0.99214 | 0.00000 | 0.99214 | 0.86325 |

Latent and semantic-observable tables agree to machine precision in this
deterministic replay (`MAE_J=0`, `MAX_J=0`, `MAE_L*=0`, `MAX_L*=0`). The blind
control collapses BLOCK and DIAGONAL locality: its h=8 diagonal/off-diagonal
information is approximately 0.25845/0.25845 for BLOCK and 0.07558/0.07558 for
DIAGONAL, while GLOBAL remains shared. This is the intended diagnostic effect
of removing family semantics.

The renderer audit found zero text collisions and zero hidden-policy leakage
across 4 families × 64 states × 4 templates. Family recovery from structured
`O` is 100%. The h=8 diagonal component-accuracy spread is 0.00094 (GLOBAL),
0.00062 (BLOCK), and 0.00128 (DIAGONAL), all below the 0.05 gate.

## Observation model

The hierarchy is:

    G -> J_latent -> psi -> J_obs -> L*_obs -> L^LLM -> T(L^LLM) -> A(t)

`O=psi(C,X)` contains domain semantics and three observable policy attributes.
The deterministic renderer `Z=phi(O)` uses four short templates per family.
The family is semantically identifiable but no synthetic family token is
rendered. The exact host decoder is only an audit/replay device; it is not a
claim about LLM comprehension.

## Corrections

The V3 audit found: (i) the old renderer was family-blind, (ii) the old oracle
was privileged with source/target IDs, (iii) the prior component gate aggregated
bit accuracies, and (iv) h-dependent RNG produced non-nested histories. V3.1
stores component 1/2/3 separately and samples one h=8 history before taking
prefixes for h=1,2,4,8. V3 artifacts are preserved unchanged.

## Observable versus latent

The primary analysis recomputes `J_latent` and `J_obs` on the same nested draws.
If `psi` is sufficient for `(C,X)`, the values should agree up to Monte Carlo
noise. `L*_obs` is compared to `L*_latent` in the same way. The blind control
removes domain identity and is intentionally not used for a future experiment.

## Hard-gate interpretation

All O1--O10 must pass before proposing paid inference. A pass means only that
the semantic observation channel preserves the intended ecological geometry in
the exact observation model. It does not mean that DeepSeek understands the
English, that the ecology is externally realistic, or that a society will
specialize.

## Future learner gate

If all gates pass, the next experiment is a small observable-geometry learner
calibration, not a society run: natural h=8, a few frozen seeds, and the three
geometry contrasts. Target scale is approximately 500--1,500 logical calls.
It should estimate realized `L^DeepSeek` against `J_obs` and `L*_obs`, including
false transfer (LLM transfer where ecological J is zero) and missed transfer
(ecological J positive but model transfer weak). It is proposed only and was
not executed here.

## Strongest caveat

V3.1 is a controlled scientific instrument, not an external-validity benchmark.
The domain semantics make family recognition deliberately explicit enough to
test the observation channel, while the shared canonical dimensions make GLOBAL
transfer engineered by design. That is acceptable for this construct-validity
phase, but later work must test whether a real model can recover the intended
semantic representation and whether transfer survives a richer ecology.
