# Post-V1 mechanism decomposition analysis plan

Status: registered development analysis; zero external inference authorized.

## Scope and data boundary

This phase uses only the clean Theory V1.1 Stage A, MICRO, and canonical MACRO
raw artifacts. Historical Theory V1 data are excluded from primary mechanism
inference because their static output instruction contained a concrete answer
vector. V1/V1.1 equations and seals are not modified. No new model calls,
probes, checkpoints, society runs, or Theory V2 equations are permitted.

Primary scientific unit: social seed within ecology (six seeds per ecology).
MICRO uncertainty unit: MICRO seed. Probe rows are repeated measurements, not
independent scientific replications.

## Frozen analyses

1. Hash raw Stage A, MICRO, MACRO event, online-step, and checkpoint files before
   and after analysis.
2. Reconstruct the complete MACRO state panel at every online step and frozen
   interval endpoint: selected agent, task niche, correctness, routing posterior
   (`alpha`, `beta_count`, `mu`), expected routing probabilities, FIFO memory
   contents/provenance/ages, and checkpoint held-out competence.
3. Double-center competence, belief, expected routing, exposure, and memory
   count/recency matrices with `P_N X P_K`.
4. Compute the exact Delta-Psi identity, reinforcement and innovation/churn
   terms, and role-update cosine with undefined zero-norm cases preserved.
5. Quantify A→mu alignment, reliability of held-out A via deterministic
   split-half probe partitions, belief calibration/staleness, posterior ranking
   error, one-step belief-policy versus current-A oracle regret, and exposure
   concentration.
6. Quantify exposure→FIFO-memory transmission, memory turnover/age/entropy/
   overlap across q, and memory→competence associations in C0 random-private.
   Adaptive exposure associations are explicitly labelled non-causal.
7. Compare MACRO memory count states with the k=8 MICRO balanced calibration
   manifold using `d_swap`; stratify available V1 prediction diagnostics by
   distance without fitting new equations.
8. Fit only the registered compact memory representation ladder (M0 counts,
   M1 recency counts, M2 slot positions, M3 pair interactions, M4 tiny tree
   ceiling) with leave-one-social-seed-out evaluation. Any flexible improvement
   is diagnostic only and cannot define Theory V2.
9. Produce signal-transmission and mechanism evidence tables for H1–H8,
   adversarial caveats, and theory-V2 readiness. Classifications remain
   descriptive development evidence, not confirmation.

## Determinism

All derived tables use fixed ordering and fixed seeds. No raw file is modified.
Any missing auxiliary journal row is reconstructed only from the matching raw
terminal completion; no imputation is allowed. Analyses are rerunnable from
the raw paths and hashes recorded in the registry.
