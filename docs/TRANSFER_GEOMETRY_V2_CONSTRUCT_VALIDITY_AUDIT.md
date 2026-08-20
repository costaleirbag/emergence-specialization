# TRANSFER-GEOMETRY-CONTROL-V1: V2 construct-validity audit

## Scope

This is a retrospective audit of the code and frozen artifacts, not a rescue of
the previous result. The source of truth is `OPEGeometryV2Ecology` and the
manifests under `reports/task-ecology/transfer-geometry-v1/manifests/`.

## What the old generator actually made

Each OPE family is evaluated by the same organizational-procedure solver with
three substantive parameters: threshold, compatibility, and exception. GLOBAL
shares threshold and compatibility but keeps the exception policy family
specific. BLOCK shares the first two parameters within ACCESS/RELEASE and
INCIDENT/PROVENANCE, while exceptions remain family-specific. DIAGONAL gives
each family all three independent factor IDs. Thus old GLOBAL is not a single
complete theta shared by all niches, and its nominal overlap matrix must not be
read as full functional identity.

The exact factor identities, realized collision frequencies over 10,000
deterministic seeds, complete symbolic-space agreement, and counterfactual
factor influence are in:

- `reports/task-ecology/ecological-information-v3/old_parameter_collision.csv`
- `old_functional_agreement.csv`
- `old_factor_influence.csv`
- `old_natural_identifiability.csv`

The audit enumerates all 768 combinations of the seven OPE fields for agreement
and factor perturbation on each frozen campaign seed. Collision frequencies use
exactly 10,000 generated environments, not model responses. Natural
identifiability uses ordinary sampled histories at h=1,2,4,8 and is separate
from the earlier greedy teaching stream.

In the 10,000-seed sweep, nominally unique exception factors collide frequently
because the old value code has only two exception values. For example, the
ACCESS--RELEASE pair is fully equal in 7,500 GLOBAL seeds and 7,500 BLOCK seeds;
the INCIDENT--PROVENANCE pair is fully equal in 2,500 seeds in those geometries.
These are realized value collisions, not evidence of intended latent sharing.
The exact pairwise counts and all factor-level frequencies are in the CSV.

## Interpretation

The old design is a useful mechanistic control for parameter sharing, but it is
not yet a clean test of functional specialization. It combines one procedural
family, shared solver structure, and a GLOBAL condition with family-specific
exceptions. Even without accidental value collisions, a model can exploit
generic procedure, output priors, or case formatting. Consequently the old
`G -> L` comparison skipped an ecology-level predictive-information check.

This does not invalidate raw transfer data. It narrows what they can support:
history-conditioned behavioral/parameter differentiation is plausible;
acquired functionally distinct roles are not established.
