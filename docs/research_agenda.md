# Research agenda: from `B` to `B(t)`

This repository studies whether initially homogeneous LLM agents can develop
task-relevant behavioral differentiation through asymmetric interaction
histories. The static behavioral matrix from the routing literature becomes a
trajectory:

\[
B(0), B(1), \ldots, B(T).
\]

The central question is not how to maximize a routing metric. It is whether
structure emerges, persists, and responds to controlled interventions.

## Three questions

1. **Emergence:** how can behavioral diversity arise from homogeneous
   initialization?
2. **Causality:** where is functional differentiation stored—individual memory,
   interaction history, or collective routing dynamics?
3. **Resilience:** after memory erasure, swap, ablation, or replacement, does a
   lost function recover, and who carries it?

The required distinctions remain:

> diversity is not specialization; specialization is not useful division of
> labor.

HSE, mutual information, utilization entropy, confidence dynamics, and routing
concentration are observables. They are not interchangeable objectives. A
terminal target should be independently meaningful (for example held-out
collective competence and robustness), especially for any future early-stop or
outer-loop optimization study.

## Current staged program

- Validate the existing matched private/shared baseline.
- Record cheap interaction observables every round and expensive probe-derived
  matrices at explicit checkpoints.
- Build matched multi-seed datasets and aggregate only permutation-invariant
  summaries unless an alignment rule is declared.
- Study feedback locality as an information-distribution condition, not a
  performance hyperparameter.
- Add memory interventions before attempting population interventions.
- Use the independent minimal model to test mechanisms qualitatively, never to
  fit or explain the DeepSeek runs.

Potential later questions include robustness, topology, population size,
trajectory prediction, and closed-loop intervention. Those require additional
design and literature review; no novelty claim is made here.

