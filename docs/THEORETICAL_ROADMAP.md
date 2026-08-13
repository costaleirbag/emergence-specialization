# Theoretical roadmap: transfer geometry to developmental dynamics

This roadmap keeps the mathematical program connected to measurable dynamics.

1. **Level 1 — empirical operator:** estimate directed `L_cd(h)` with forced
   exposure, placebo controls, retention delays, and environment-seed pairing.
2. **Level 2 — linear stability:** study centered `T(L)` and the exchangeable
   state under competence-sensitive allocation.
3. **Level 3 — finite capacity:** add bounded memory/competence constraints and
   simplex-valued competence.
4. **Level 4 — finite-N stochastic dynamics:** include sampling noise, provider
   variance, and random allocation.
5. **Level 5 — nonlinear fixed points:** characterize attractors beyond the
   linear neighborhood.
6. **Level 6 — persistence:** define role persistence and metastability under
   retention, forgetting, and perturbation.
7. **Level 7 — interventions:** test ablation, transplantation, and regeneration
   only after the transfer-to-organization link is preregistered.
8. **Level 8 — scaling:** vary population size `N`, niche count `K`, memory
   capacity, and task frequencies.

Open questions include when centered `L` stabilizes exchangeability; which
eigenspaces encode winner-take-all versus block specialization; how finite
capacity changes spectra; whether negative transfer creates stable niches;
whether asymmetric `L` yields cycles; the finite-N stochastic analogue; and
which order parameter separates behavioral diversity from competence-organized
specialization.

The eigenvalue condition is a result of the explicit effective model only. It is
not a claim about DeepSeek internals and does not replace a future society test.

## Theory-to-observable map

| theoretical object | empirical observable | interpretation |
|---|---|---|
| `L_cd(h)` | held-out source→target gain | directed learning/transfer |
| `T(L)` | centered transfer matrix | niche-contrast drive in the effective model |
| `chi(L)` | largest real eigenvalue | model-dependent susceptibility, not specialization |
| contrast eigenspace | competence-mode projection | alignment of differentiation with ecology |
| competence vector `a_i` | competence matrix `A(t)` / `Phi` | functional differentiation, not HSE |
| agent allocation `p_i(c)` | `I(C;R)`, utilization, `eta_route` | organized labor/allocation |
| team utility | oracle gain / matching gain | useful complementarity |
| behavioral output vector | HSE | response diversity only |

## Future predictions, conditional on a controlled ecology

These are hypotheses for a separately approved society protocol:

- weak centered spectrum in GLOBAL should favor comparatively generalist
  competence under moderate competence-sensitive allocation;
- a BLOCK operator with a dominant `(1,1,-1,-1)` mode should produce earliest
  competence contrasts aligned with that block mode;
- a DIAGONAL operator with near-degenerate contrast modes should permit
  different agent-label assignments across runs while preserving ensemble
  permutation symmetry;
- non-normal transfer may produce transient competence differentiation without
  persistent roles.

None of these predictions licenses a society run in the present protocol.

## Theory V1 closure (2026-08-13)

The frozen Theory V1 challenge is closed after a raw-data forensic repair. The
repaired evaluation confirms that `K`, `T_k`, and `J` are useful analysis
objects, but the frozen linear reduction did not meet its prospective T1–T9
predictive criteria. The repaired `T(L)`-like spectra remain model-dependent
mathematical diagnostics, not an observed LLM-society Jacobian. MICRO and MACRO
data are consumed and may only inform a separately approved future theory; no
Theory V2 equations or new experiment are defined here.

## Theory V1 prospective challenge (2026-08-12)

The project now separates old DEVELOPMENT observations from a future
parameterization/test boundary. Theory V1 freezes the local operator and
linearized effective dynamics in [THEORY_V1_FROZEN.md](theory/THEORY_V1_FROZEN.md).
New MICRO data may estimate only `K^(4)`, `K^(8)`, and `K^(12)`; predictions must
be committed before any MACRO social observations. The fixed challenge uses two
fresh ecology/seed spaces and 212,480 logical calls. The current repository
contains only offline preparation and mock validation; no Theory V1 social data
exist and no Theory V2 is defined.

## Ecology-level prerequisite (V3)

Before interpreting a measured `L` or its centered operator, the task ecology
must itself be audited. V3 defines `J_cd(h)=I(Y_d;H_c^(h)|X_d)` and Bayes gain
`L*` under an explicit synthetic prior. Its tested hierarchy is `G -> J -> L*`;
the subsequent `L_model -> T(L)` link remains empirical/model-dependent. The
V3 synthetic gates pass, but this is only a construct-validity precondition. A
future model calibration must still test objective held-out transfer, natural
vs teaching exposure, and foreign-theta specificity before any society run.

## Observation-channel questions

V3.1 adds an explicit measurement layer between ecology and learner:
`G -> J_latent -> psi -> J_obs -> L^m`. Open questions are which semantic
observation channels preserve transfer geometry; how to quantify representation
loss; how learner parsing changes `J_obs -> L^m`; whether two learners in one
latent ecology experience different effective ecologies; whether pretrained
semantics introduce cross-niche transfer absent from the ecology; and how
stochastic/noisy observation should enter the future social dynamical model.

## Calibration status (2026-08-09)

The transfer-geometry control completed, but the primary natural matrices did
not recover a stable GLOBAL/BLOCK/DIAGONAL ordering. The effective theory is
therefore a conditional analysis tool, not a validated predictor of society
dynamics. Before a society protocol, the ecology gate must decide whether the
weak and variable natural transfer is a meaningful negative control or whether
the task generator requires a separately approved identifiability repair.

## Learner calibration V1 (2026-08-09)

The observable ecology now has a direct model-response layer. DeepSeek Direct
realized small and heterogeneous gains after natural h=8 histories, with a
partial BLOCK diagonal signal but no preregistered GLOBAL/BLOCK/DIAGONAL
ordering. Therefore `L^DeepSeek` is measured, but its mapping from `J_obs` and
`L*_obs` is not yet a validated substrate for social dynamics. `T(L^DeepSeek)`
may be computed as an effective-model object, but must not be described as a
society Jacobian or used to authorize a society run.

## Learner calibration V2 (2026-08-09)

V2 is the harness-corrected realization layer. The exact observable ecology had
strong Bayes opportunity before inference, but DeepSeek realized only a partial
geometry: diagonal gains were positive, GLOBAL off-diagonal transfer was
negative, BLOCK within-block transfer was absent, and the preregistered Q
ordering failed. The appropriate theoretical status is therefore:

`G -> J_obs -> L*_obs` established offline; `L^DeepSeek` measured but not
qualified; `T(L^DeepSeek)` analyzable only as a conditional effective-model
object; society dynamics not tested.

New learner-level questions are whether `M_m` preserves locality, flattens or
rotates ecological geometry, how context length and semantic parsing alter the
map, and whether zero-information transfer reflects a pretrained prior. No
society experiment should be designed around a partial learner geometry without
principal-researcher review.

## Regime observability extension (2026-08-10)

The ecology hierarchy now distinguishes a designed meta-ecology from its realized
regime:

`p(G) -> G -> Theta -> H -> R -> q_m(G,Theta | H,R) -> L^m -> T(L^m)`.

`J_cond` and `L*_cond` remain correct for a learner that knows `G`. They are not
automatically learner-available when `R=null`. The hidden-regime oracle
marginalizes `G` under an explicit experimenter prior; the relation oracle
conditions only on `SAME_POLICY`/`INDEPENDENT_POLICY`; the full oracle is the old
privileged reference.

If regime is unknown in a future society, agent state may need a belief
`q_i(G,t)`. A conceptual effective transfer is
`L_i(t)=Σ_g q_i(g,t)L_i(g,t)`, coupling ecology identification to competence
development. This is a future model, not an empirical law or implemented
mechanism.

## Relation-signal causal transfer V1 (2026-08-10)

The relation-cue intervention is now an empirical learner response layer. It was
technically CLEAN but **PARTIAL RELATION CONTROL**: `Gamma_R` and `Upsilon_R`
were near zero, BLOCK structure was below threshold, and the preregistered
GLOBAL/BLOCK/DIAGONAL Q ordering failed. Relation-oracle alignment alone was
positive for BLOCK/DIAGONAL but did not qualify the learner geometry. The next
decision is therefore diagnostic, not social: distinguish relation parsing,
context interference, joint-output composition, and answer/action copying before
any society experiment. `T(L^DeepSeek)` remains a conditional effective-model
object, never an automatically observed LLM-society Jacobian.
## Cross-domain bottleneck V1 (2026-08-10)

The learner map now has a representation ladder diagnosis. An explicit semantic
correspondence improved natural cross-domain transfer, canonical histories helped
more, and explicit policy tables nearly solved the task. The remaining map from
resolved examples to an executable reusable policy is therefore a central open
object. The evidence is compatible with a rule-induction or history
representation bottleneck, but does not identify a unique internal mechanism.

The next theory-relevant diagnostic should separate multi-example induction,
joint-output composition, target semantic parsing, and context/order effects
before any social amplification is modeled. The frozen V1 population cannot
identify BLOCK cross-block or DIAGONAL cross-domain contrasts, so those missing
cells must not be filled by theoretical assumptions.

## Track separation after local plasticity V1 (2026-08-10)

### Track A — minimal developmental society

The local-plasticity curve passed all six microscopic qualification gates:
same-niche experience produced useful absolute gain and exceeded independent
foreign context at h=8, with a positive descriptive dose response. Track A can
now be designed as a minimal causal society experiment using adaptive routing,
private memory, and preregistered controls.

### Track B — learner ecology / transfer

The `J`, `G`, relation, and `Pi` questions remain informative but are not a
prerequisite for the first clean Track A test. Keep cross-domain scaffolding
closed unless a separately approved learner question reopens it.

### Track C — strong effective theory

Measured transfer operators and `T(L)` remain conditional theoretical objects.
They are not automatically an LLM-society Jacobian and should not be used to
complicate the minimal society protocol.

## Minimal developmental society V1 (frozen, awaiting result)

Track A now has a preregistered causal test of the next arrow:

```text
local plasticity + competence-sensitive allocation
    -> held-out agent×niche competence interaction
```

The primary finite-system statistic is the double-centred competence energy
`Psi_spec`, with random-private, adaptive-private at beta 4 and 12, and
adaptive-shared beta 12 controls. A positive statistic is not sufficient for a
claim of functional specialization: routing alignment, matching gain, team
utility, role persistence, and across-seed label symmetry remain separate
checks. The experiment is frozen at eight seeds and 128 rounds; no intervention
or post-result tuning is authorized.

## Minimal developmental society V1 — corrected analysis status (2026-08-11)

The first social campaign is now **ALREADY EMPIRICAL**, with one important
provenance correction. The initial offline competence aggregation mixed niche
accumulators and generated impossible accuracies. Recomputing from raw
checkpoint events fixed the analysis without changing the paid experiment.

```text
private developmental state
    -> agent×niche competence interaction (H1–H3: pass)
    -> competence-aligned routing and matching (H4–H5: pass)
    -> realized team utility (H6: fail)
```

This supports social amplification and partial functional organization in the
frozen eight-seed pilot, but not the stronger claim of emergent useful
specialization. `Psi_spec` remains an interaction statistic, not a role ontology
or a phase-transition order parameter. Future theory should treat the corrected
competence matrices as empirical inputs and keep team utility, role persistence,
and across-seed symmetry as separate requirements. No society follow-up is
authorized by the analysis repair.
