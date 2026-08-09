# OPE information geometry V3 specification

Status: offline construct-validity instrument only. No model inference is part
of this specification.

Families are `ACCESS`, `RELEASE`, `INCIDENT`, and `PROVENANCE`. Each case has
three observed policy dimensions in `{0,1,2,3}` and three binary outputs. All
six balanced 4-to-2 maps are equally likely for each hidden component. The
three components are conditionally independent given the hidden theta vector.

| geometry | latent sharing |
|---|---|
| GLOBAL | one theta vector for all four families |
| BLOCK | ACCESS/RELEASE and INCIDENT/PROVENANCE, independently |
| DIAGONAL | one theta vector per family; accidental equality is not information |

`G` is the resulting 4x4 same-latent matrix. `J`, `J_normalized`, `A*`, and
`L*` are computed by exact posterior prediction and deterministic Monte Carlo
over the known synthetic prior. Natural histories are the primary estimand;
greedy teaching histories are an optional positive control.

Pre-registered gates are evaluated in the audit report: diagonal information,
global/block locality, diagonal low off-diagonal information, diagonal learning
gain, ordered `Q*`, component-baseline sanity, and independent-cell zero checks.
Failure means “do not recommend an LLM ecology run”; it is not a failure of the
software.
