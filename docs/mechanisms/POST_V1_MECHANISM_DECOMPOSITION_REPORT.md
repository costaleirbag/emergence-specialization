# Post-V1 mechanism decomposition

## Executive answer

The clean V1.1 data do not support a single repaired V1 loop. The strongest
descriptive bottleneck is downstream of exposure: adaptive routing creates large
and beta-sensitive exposure asymmetries, and those asymmetries reach FIFO memory,
but changes in held-out competence move against the existing role direction.
Across both ecologies and intervals, the reinforcement term in the exact
Delta-Psi identity is negative on average while the innovation term is positive.
The result is differentiation churn rather than stable reinforcement. A second,
non-independent candidate is poor router-belief tracking of current competence;
however split-half reliability of A is low, especially in AFFINE, so this claim
must remain cautious. Sharing clearly changes memory timescale, not only
cross-agent similarity.

No new model calls were made. Theory V1 and V1.1 remain closed/consumed;
Theory V2 is not defined.

## Data and provenance

Primary data are the clean V1.1 Stage A, MICRO, and canonical MACRO raws. The
five raw SHA-256 values and their before/after equality are in
`reports/post-v1-mechanisms/summary.json`; all are unchanged. MACRO has 62,976
terminal logical observations from 62,995 physical attempts, with the recorded
technical retries and one provider fingerprint. Historical V1 data were not used
as primary evidence. The analysis registry was frozen before derived results.

## Measurement reliability

Competence is measured from eight held-out probes per agent–niche–checkpoint.
Deterministic even/odd split-half reliability is modest in V31 (Pearson about
0.29–0.36 across checkpoints; Spearman–Brown about 0.10–0.47) and near zero in
AFFINE (Pearson about 0.04–0.11). Therefore weak A–mu alignment and weak
memory→A prediction have a low measurement ceiling. This is a limitation, not a
reason to convert noisy estimates into a positive mechanism claim.

## The feedback loop

The reconstructed chain is `A → mu → p → E → M → A'`. The stored router
posterior is reproduced exactly from initial Beta(1,7) state and online
correctness; the frozen routing probabilities reproduce selected agents from
the stored routing uniforms. The full state panel contains posterior counts,
mu, expected routing, task assignment, correctness, FIFO slot niche/timestamp,
sharing provenance, and held-out A at all checkpoints.

At endpoint t=128, A–mu centered cosine averages are about 0.14 (AFFINE) and
0.24 (V31) over the private beta grid, while top-agent agreement is only about
0.13–0.63 depending on beta/ecology. The mu→p policy edge is mathematical, not
an inferred causal claim; for beta>0 its centered alignment is high. The
exposure→memory edge is also comparatively strong (C4 about 0.6–0.9 in private
conditions). The weak edge is memory→future role movement: C5 is variable and
the direct A→Delta-A cosine is negative at endpoint.

## Does beta amplify signal or noise?

Increasing beta generally increases `||Z_E||` and `||Z_M||` in private cells.
For example, V31 endpoint exposure norm rises from about 5.84 at beta=0 to
17.27 at beta=20; AFFINE rises from 5.49 to 12.40. Yet belief-policy regret
also rises from zero at beta=0 to roughly 0.038 (V31) and 0.048 (AFFINE) at
beta=20, while current A–mu error remains roughly 0.39–0.44. This is consistent
with a selection-on-noise/lock-in candidate, but not a causal estimate of a
counterfactual society.

## Routing, exposure, and FIFO memory

The random-private C0 diagnostic gives a cleanest available associational view
because routing is uniform with respect to competence. In a simple exposure
model controlling starting A, the own-niche exposure coefficient is positive in
both ecologies (approximately +0.030 V31 and +0.010 AFFINE), while foreign
exposure is negative. These rows remain clustered by ecology×seed and are not
claimed as causal society effects.

Sharing changes the time scale sharply. At t=128, q=0 memories have mean item
age about 16–24 tasks and temporal span about 27–32; q=.5 has mean age about 6
and span about 11; q=1 has mean age 3.5 and span 7. Exact-case overlap is near
0 at q=0, about 0.37 at q=.5, and 1.0 at q=1. Thus “sharing = scalar
homogenization” is inadequate as a state description; q also changes how much
recent global history replaces older local history.

## Delta-Psi: reinforcement versus churn

For every interval the exact identity

`Delta Psi = 2<Z0,DeltaZ>/(NK) + ||DeltaZ||²/(NK)`

holds to machine precision. Across endpoint intervals, mean reinforcement is
negative in both ecologies (approximately −0.0080 AFFINE and −0.0128 V31 in
private beta=12) while mean innovation is positive (about +0.0084 and +0.0140).
Mean Delta-Psi remains small and positive because innovation offsets the negative
reinforcement. Cosine role-update is negative in the same cells (about −0.56 to
−0.81). This is the clearest evidence that behavioral/competence
differentiation does not necessarily preserve a stable role direction.

## Memory → competence and representation ladder

The held-out social-seed memory ladder finds no robust improvement over the
count-only M0 baseline. Mean OOF R² is slightly negative for M0 and becomes more
negative for M1 recency, M2 slot position, M3 pair interactions, and the tiny
M4 tree ceiling in both ecologies. This does not prove that counts are the true
state; it says that the available six-seed, eight-probe data do not identify a
more informative generic representation. The correct classification is
INCONCLUSIVE, not “memory is linear.”

The MICRO-to-MACRO distance audit finds substantial but not overwhelming local
coverage. At t=128, the fraction of agent memories within `d_swap≤2` is about
0.55 in V31 and 0.81 in AFFINE. Residual growth error does not increase
consistently with distance (V31 far states are somewhat worse; AFFINE far states
are not), so local-K extrapolation is not a sufficient explanation on this
evidence.

## Mechanism candidates H1–H8

The registered evidence table gives the detailed rows. The conservative
development classifications are:

| candidate | classification | reason |
|---|---|---|
| H1 router staleness | INCONCLUSIVE | recency EWMA improves OOF MAE modestly in both ecologies, but A reliability is low |
| H2 selection-on-noise | INCONCLUSIVE | beta raises exposure and regret, but no causal adaptive intervention exists |
| H3 exposure-memory attenuation | INCONCLUSIVE | E→M transmission is visible, but the downstream contrast is not identified causally |
| H4 memory-state insufficiency | INCONCLUSIVE | no M1–M4 held-out improvement over M0; no positive representation identified |
| H5 MICRO–MACRO extrapolation | INCONCLUSIVE | local support is partial, but residual error is not monotone in distance |
| H6 sharing-timescale | MODERATE | q changes age, span, occupancy, and exact-case overlap in both ecologies |
| H7 differentiation churn | INCONCLUSIVE | negative reinforcement and role-update cosine are consistent, but A is noisy |
| H8 multiple bottlenecks | MODERATE descriptive synthesis | several transmission edges are weak; this is not a fitted causal decomposition |

## Why the V1.1 tests failed

- **V11-A:** beta increases exposure concentration, but not a reliable positive
  role-growth ordering; the direction of competence movement is unstable.
- **V11-B:** matched effective routing gain is not equivalent at the observed
  operating scale, consistent with the effective reduction missing state/noise
  dependence.
- **V11-C:** sharing changes FIFO age and overlap, so a scalar retention law does
  not capture its effect on current competence.
- **V11-D:** adaptive exposure does not amplify stable comparative advantage;
  its incremental changes are small/negative and often anti-aligned with the
  current role direction.

## Strongest bottleneck and adversarial review

The strongest current candidate is **failure of memory/exposure changes to
reinforce a persistent competence direction**, with router staleness and
sharing-induced timescale changes as plausible contributors. This is not a
rescued theory: the memory model ladder did not identify a simple missing state,
and low A reliability prevents a strong claim about stale beliefs. The same
pattern appears in both ecologies, but only six seeds per ecology are available.
The result could still reflect transient prompt competence rather than acquired
skill, finite-probe noise, or an insufficient specialization observable.

## Theory V2 readiness

**NOT READY — MORE CONCEPTUAL WORK NEEDED.** A future formalization would need
separate current competence, cumulative belief, FIFO age/provenance, and
role-direction churn, as listed in
`POST_V1_THEORY_REQUIREMENTS.md`. The current data do not identify a compact
transparent replacement that improves held-out seed prediction. A paper framed
around the failure of the local-learning feedback loop may be stronger than
adding terms to Theory V1 without a new measurement and calibration design.

No Theory V2 equations, new experiment, or paid call was created.

**NEXT ACTION: PRINCIPAL RESEARCHER REVIEW.**

## Explicit answers to the mechanism questions

1. **Does the router know which agents are currently competent?** Only weakly
   in these measurements. `mu` is exactly reconstructible, but its centered
   alignment with current held-out `A_bit`, top-agent agreement, and split-half
   reliability are modest/unstable; this is not a clean router-failure causal
   result because the competence estimate is noisy.
2. **Does beta amplify signal or posterior noise?** It amplifies exposure
   concentration and one-step belief-policy regret together. The offline data
   support a selection-on-noise candidate, not a causal estimate.
3. **Do routing asymmetries create persistent memory asymmetries?** Yes for the
   reconstructed FIFO state: exposure and memory-count interaction norms rise
   in private beta cells. Persistence as useful competence is not established.
4. **Does current memory asymmetry predict held-out comparative advantage?** Not
   robustly: the held-out memory ladder does not beat count-only M0 and the
   random-private regression is associational.
5. **Are macro states inside the MICRO region?** Partly. The `d_swap` audit is
   reported per checkpoint; endpoint support is about 0.55 within radius 2 in
   V31 and 0.81 in AFFINE. Distance does not yield a consistent residual-growth
   gradient.
6. **Does recency/order beat counts?** No reliable held-out improvement appears
   for M1--M4 or the deterministic slot-order ablation. This is an inability to
   identify a better representation, not proof that memory is count-linear.
7. **Does cumulative belief become stale?** Recency EWMA is modestly better in
   OOF MAE in both ecologies, but reliability and six-seed clustering make H1
   inconclusive.
8. **Does sharing only homogenize?** No. Sharing changes age, temporal span,
   update rate, provenance mix, and exact-case overlap; homogenization is only
   one consequence of a timescale change.
9. **When Psi changes, what drives it?** The exact decomposition shows positive
   innovation/churn offsetting negative reinforcement on average. A changing
   Psi therefore need not mean stable roles are being reinforced.
10. **Why does local plasticity fail to close the loop?** The best current
    explanation is downstream closure failure: exposure reaches FIFO memory, but
    memory-driven updates do not reliably reinforce the existing competence
    direction. This is a descriptive candidate, not a causal verdict.
11. **Is one bottleneck sufficient?** No single bottleneck is identified. The
    evidence is compatible with several moderate losses plus measurement noise.
12. **Is Theory V2 justified?** No. No compact state representation improves
    held-out seed prediction, so the registered readiness criterion is not met.

## Reproducibility and diagnostic scope

`state_panel.csv` contains 198,144 rows including the empty t=0 state and all
128 sequential online states for 96 trajectories × 4 agents × 4 niches. Each
row preserves router counts, posterior mean, expected routing, routing and
sharing draws, recipient list, FIFO memory contents/timestamps/provenance, and
checkpoint `A_bit`, `A_joint`, `Psi_bit`, and `Psi_joint` where defined. The
companion tables include temporal diagnostics, winner's-curse/regret fields,
negative controls, cross-ecology memory-model transport, order ablations, and
the exact raw hash manifest. Running the module twice from the same raws is
deterministic up to figure metadata.

No historical harness-confounded V1 data enter these primary tables. No
response-level row is treated as an independent society replicate: the
uncertainty unit remains ecology × social seed. The `T`/spectrum and any
centered alignment are diagnostics under the existing effective-model notation,
not a claim that the LLM society has that literal Jacobian.

## Paper-level implication

The defensible contribution at this stage is a failure decomposition of the
feedback loop: behavioral diversity and exposure asymmetry can coexist with
weak, noisy, or reversing competence reinforcement. A simpler account of why
local plasticity fails to become stable social specialization is preferable to
adding an unvalidated Theory V2. Any future theory must be frozen prospectively,
respect reliability ceilings, represent FIFO age/provenance, and win held-out
seed prediction before it is tested socially.
