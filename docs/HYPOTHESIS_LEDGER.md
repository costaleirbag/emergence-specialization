# Hypothesis ledger

Qualitative priors are deliberately coarse. Only the PI session changes final
statuses. `SUPPORTED` means supported within the tested protocol and claim
level; it never means universal truth.

## H1 — contextual anchoring

- **Statement:** persistent memory primarily biases future output toward labels
  visible in context rather than teaching an abstract hidden rule.
- **Mechanism:** recency/frequency-sensitive copying or contextual response bias.
- **Prior:** HIGH.
- **Supporting evidence:** high any-memory-label copy rates in shared clean v2;
  memory changes confidence and answer reliability without a monotone accuracy
  curve; correct and truly corrupted feedback were not cleanly separated in the
  completed thinking-off calibration.
- **Contradicting evidence:** observational label overlap can be mechanically
  high with eight labels in memory; current analyses are not causal order
  interventions.
- **Alternatives:** ordinary in-context induction plus stochastic execution;
  label-frequency coincidence; provider sampling dependence.
- **Cheapest discriminating test:** existing-data conditional anchoring analysis
  with exact probe identity and memory-label baselines.
- **Stronger test:** matched original/reversed/shuffled memory order with rank-full
  examples and untouched balanced probes.
- **Status:** OPEN.
- **Last update:** 2026-08-08 session initialization.

## H2 — shared-memory synchronization

- **Statement:** shared memory lowers behavioral diversity by exposing agents to
  common contextual anchors that synchronize answer distributions.
- **Mechanism:** common context contracts between-agent behavioral variation.
- **Prior:** HIGH.
- **Supporting evidence:** clean-v2 pairwise probe answer agreement rises to
  0.654 (confidence/shared) and 0.708 (random/shared) at t=20, versus 0.334 and
  0.438 in matched private cells.
- **Contradicting evidence:** common memories may synchronize genuine learned
  rules rather than simple anchors; provider/common-prompt effects remain.
- **Alternatives:** shared competence homogenization; measurement geometry;
  correlated provider sampling.
- **Cheapest discriminating test:** condition on memory-label content and compare
  agreement/excess anchoring in existing clean-v2 probes.
- **Stronger test:** causal memory-order/content-preserving intervention.
- **Status:** OPEN.
- **Last update:** 2026-08-08 session initialization.

## H3 — private-history phenotypic divergence

- **Statement:** different private histories generate persistent behavioral
  biases even without different competence.
- **Mechanism:** path-dependent contextual state differs across agents.
- **Prior:** HIGH.
- **Supporting evidence:** private/shared HSE contrast survives random routing;
  Phi and functional alignment remain weak while behavioral HSE differs.
- **Contradicting evidence:** private contexts also differ in informational
  adequacy and may induce genuine competence heterogeneity.
- **Alternatives:** finite-sample HSE; stochastic provider variation; competence
  differences too noisy for current probes.
- **Cheapest discriminating test:** anchoring-only toy model and raw conditional
  analyses.
- **Stronger test:** memory-content transplant/order intervention with held-out
  coefficient recovery.
- **Status:** OPEN.
- **Last update:** 2026-08-08 session initialization.

## H4 — insufficient rule induction

- **Statement:** V4 Flash in thinking-off mode does not reliably infer current
  modular affine rules from at most eight examples under the frozen prompt.
- **Mechanism:** induction/prompt bottleneck rather than lack of formal
  identifiability.
- **Prior:** HIGH.
- **Supporting evidence:** two calibrations show weak, non-monotone held-out
  accuracy close to balanced-label baseline.
- **Contradicting evidence:** the rank/identifiability of the exact contexts has
  not yet been audited; arithmetic execution may be the bottleneck.
- **Alternatives:** rank-deficient contexts; execution failure; serialization;
  output-protocol interference.
- **Cheapest discriminating test:** exact GF(7) rank audit.
- **Stronger test:** rank-full coefficient-inference control evaluated offline.
- **Status:** OPEN.
- **Last update:** 2026-08-08 session initialization.

## H5 — memory serialization bottleneck

- **Statement:** full Experience serialization encourages prediction-copying and
  suppresses induction relative to clean input/output feedback examples.
- **Mechanism:** irrelevant previous-prediction/confidence fields dominate
  attention or framing.
- **Prior:** MEDIUM.
- **Supporting evidence:** full experience produces much higher confidence than
  feedback-only in the off arm.
- **Contradicting evidence:** k8 held-out accuracy is nearly identical between
  representations; neither representation clearly learns.
- **Alternatives:** both prompts fail for another reason; confidence difference
  is cosmetic.
- **Cheapest discriminating test:** prompt-token/salience audit.
- **Stronger test:** rank-full coefficient recovery across frozen
  representations.
- **Status:** AMBIGUOUS.
- **Last update:** 2026-08-08 session initialization.

## H6 — reasoning bottleneck

- **Statement:** the same model can learn the rule with genuine reasoning, while
  thinking-off fails.
- **Mechanism:** latent coefficient induction requires a reasoning trajectory.
- **Prior:** MEDIUM.
- **Supporting evidence:** no valid comparative evidence; only technical signs
  that the API produced long reasoning traces.
- **Contradicting evidence:** thinking-on arm was incomplete and final JSON often
  absent; no scientific comparison is valid.
- **Alternatives:** execution/prompt bottleneck persists with thinking; model
  cannot reliably solve modular systems.
- **Cheapest discriminating test:** official API/protocol audit and tiny final-
  answer smoke, if affordable.
- **Stronger test:** small rank-full coefficient-inference experiment with
  preregistered token/cost cap.
- **Status:** AMBIGUOUS.
- **Last update:** 2026-08-08 session initialization.

## H7 — execution bottleneck

- **Statement:** even with the correct rule, the model cannot reliably evaluate
  modular affine functions on unseen inputs.
- **Mechanism:** arithmetic/modulo execution errors.
- **Prior:** MEDIUM.
- **Supporting evidence:** current end-to-end accuracy is weak, but induction and
  execution are confounded.
- **Contradicting evidence:** no explicit-rule control has yet isolated
  execution.
- **Alternatives:** induction alone fails while execution is strong.
- **Cheapest discriminating test:** explicit-rule balanced held-out control.
- **Stronger test:** compare model answer with offline execution of a separately
  inferred coefficient triple.
- **Status:** OPEN.
- **Last update:** 2026-08-08 session initialization.

## H8 — confidence bottleneck

- **Statement:** self-reported confidence contains little competence information.
- **Mechanism:** confidence reflects prompt/context style or response fluency
  rather than correctness.
- **Prior:** HIGH.
- **Supporting evidence:** calibration AUROC is near/below 0.5 in several cells;
  clean-v2 routing alignment is weak despite confidence routing.
- **Contradicting evidence:** pooled AUROC may obscure conditional signal by
  world/context; ten-seed power is limited.
- **Alternatives:** competence itself is absent, so no confidence signal could
  appear.
- **Cheapest discriminating test:** existing-data hierarchical/within-context
  confidence diagnostics.
- **Stronger test:** first establish learnable competence, then test signal
  conditional on competence.
- **Status:** SUPPORTED.
- **Last update:** 2026-08-08 session initialization, provisional within current
  protocol.

## H9 — exemplar identifiability

- **Statement:** some calibration contexts fail because their examples do not
  uniquely identify `(a,b,c)` over GF(7).
- **Mechanism:** design matrix rank below three.
- **Prior:** MEDIUM.
- **Supporting evidence:** k=1 and k=2 cannot uniquely identify three
  coefficients in principle.
- **Contradicting evidence:** k=4/k=8 random contexts are likely often full rank,
  but exact audit is pending.
- **Alternatives:** contexts are identifiable and the model still fails.
- **Cheapest discriminating test:** exact rank audit of every context.
- **Stronger test:** rank-full-only coefficient-inference experiment.
- **Status:** OPEN.
- **Last update:** 2026-08-08 session initialization.

## H10 — stochastic measurement

- **Statement:** a substantial part of behavioral geometry is sampling/provider
  stochasticity rather than persistent agent state.
- **Mechanism:** identical prompts produce different sampled answers and
  confidence values.
- **Prior:** HIGH.
- **Supporting evidence:** corrected repeated-call agreement is modest in many
  exact prompt groups; HSE is nonzero at t=0.
- **Contradicting evidence:** shared/private trajectories diverge systematically
  across conditions and routing strategies.
- **Alternatives:** state effects plus stochastic noise.
- **Cheapest discriminating test:** reliability-adjusted existing-data analysis.
- **Stronger test:** more identical-prompt replicates on untouched contexts.
- **Status:** SUPPORTED.
- **Last update:** 2026-08-08 session initialization, as a contributor rather
  than a complete explanation.

## H11 — finite-memory interference

- **Statement:** recent-k/mixed memory dilutes or displaces niche-relevant
  examples and prevents stable competence acquisition.
- **Mechanism:** fixed context capacity plus heterogeneous task stream creates
  interference.
- **Prior:** MEDIUM.
- **Supporting evidence:** mixed and larger-k contexts do not show monotone
  learning; private recent-k memories are sparse per world.
- **Contradicting evidence:** same-world calibrations also fail, so cross-world
  dilution is not necessary to explain failure.
- **Alternatives:** general induction/execution failure.
- **Cheapest discriminating test:** compare rank/full-context and per-world
  memory composition offline.
- **Stronger test:** only after learnability exists, a preregistered memory-
  capacity/interference calibration.
- **Status:** WEAKENED.
- **Last update:** 2026-08-08 session initialization.

## H12 — HSE without functional organization

- **Statement:** behavioral HSE can rise through contextual-state divergence
  while competence structure and useful allocation remain weak.
- **Mechanism:** anchor-biased response distributions differ without rule
  learning.
- **Prior:** HIGH.
- **Supporting evidence:** clean-v2 private cells maintain higher HSE while Phi,
  routing alignment, and competence gains are small; single-agent calibrations
  show weak learning.
- **Contradicting evidence:** current competence probes may be noisy and HSE may
  still contain a functional component.
- **Alternatives:** real but undermeasured competence differentiation.
- **Cheapest discriminating test:** anchoring-only null simulation and HSE
  sensitivity.
- **Stronger test:** causal order intervention plus coefficient recovery.
- **Status:** SUPPORTED.
- **Last update:** 2026-08-08 session initialization, limited to claim that the
  current data are compatible with and illustrate this separation.

## H13 — task-ecology transfer geometry

- **Statement:** acquired functional specialization requires a task ecology with
  learnable, capacity-constrained and non-flat transfer geometry; the current
  coefficient-varying GF(7) worlds may be a mechanistic/null ecology rather than
  a construct-valid substrate for broad procedural roles.
- **Mechanism:** targeted exposure creates comparative advantage only when
  `L_cc` exceeds relevant cross-family `L_cd`, or when the directed transfer
  matrix has useful block/asymmetric/interference structure.
- **Prior:** HIGH that ecology matters; MEDIUM that GF(7) is structurally too
  narrow for the broad role construct.
- **Supporting evidence:** all worlds share one affine-modular operation; existing
  non-alias calibrations show little positive same-world learning; current
  literature on task transfer and recent heterogeneous-agent evolution treats
  task relations as substantive rather than labels.
- **Contradicting evidence:** coefficient knowledge is world-specific, so GF(7)
  could still yield a diagonal `L` and a narrow parameter-specialization result
  if learning worked. That has not been cleanly demonstrated or refuted under a
  rule-aware positive-control protocol.
- **Alternatives:** the task ecology is adequate but DeepSeek thinking-off, the
  renderer, arithmetic execution, or memory budget is the true bottleneck.
- **Cheapest discriminating test:** existing-data non-alias estimate of GF(7)
  diagonal versus unrelated exposure, plus explicit-rule execution to isolate
  arithmetic.
- **Stronger test:** prevalidate a generated semantic/procedural ecology and
  estimate the full randomized single-agent `L_cd(h)` matrix before any society.
- **Status:** OPEN.
- **Last update:** 2026-08-08 ecology-priority steer.

