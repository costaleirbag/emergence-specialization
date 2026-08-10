# Relation-Signal Causal Transfer V1

**Frozen single-agent intervention; no society run.**

## Question

Does changing only a learner-visible statement about the source-target policy
relation causally control whether DeepSeek applies a source-domain policy to a
cross-domain target? The intervention follows the V2 harness correction and the
offline ecology-regime observability audit.

## Frozen model and ecology

- DeepSeek Direct, `deepseek-v4-flash`, thinking off.
- V3.1 semantic ecology and completed V2 manifest reused exactly.
- Seeds 9201–9204; natural resolved h=8 histories; eight V2 probes.
- Cross-domain only: 3 geometries × 4 seeds × 12 ordered source-target pairs ×
  8 probes = 1,152 underlying tasks.
- No new histories, probes, maps, templates, factor correspondence, theta,
  geometry name, explanation, confidence, or reasoning.
- Existing V2 responses are historical `R_NONE`; they are not rerun.

## Intervention arms

Every underlying task receives all three cues, in a frozen interleaved physical
order:

- **R0:** “Policy relationship: whether the hidden decision policy governing the
  previous resolved cases is the same as the hidden decision policy governing the
  current case is not specified.”
- **RS:** “Policy relationship: the previous resolved cases and the current case
  are governed by the same hidden decision policy for their corresponding
  attributes.”
- **RI:** “Policy relationship: the hidden decision policy governing the previous
  resolved cases was generated independently of the hidden decision policy
  governing the current case.”

The cue is inserted immediately before the unchanged V2 history renderer. RS or
RI can therefore be counterfactual/misleading relative to the host ecology. This
is intentional: it is a causal intervention on model input, not a claim that the
counterfactual cue is truthful.

## Calls, budget, and retry policy

`3 × 1,152 = 3,456` new logical completions; no baseline or same-family calls.
The hard external ceiling is **US$0.15**, including retries. The freeze command
uses actual V2 transfer costs and rendered cue prompts, requiring a 50% safety
margin below the ceiling. Technical transport/empty/parse failures may retry at
most once. Valid wrong answers and semantic OOD outputs are terminal scientific
observations and are never retried.

## Source-policy precondition

For each underlying task, the host computes the exact posterior over the true
source policy given the h=8 history and target X. The source-policy action is
stored as audit metadata and never placed in the model prompt. The primary
source-policy subset is `A*_source >= 0.99`; the frozen gate requires at least
90% of the 1,152 tasks. The preflight manifest records the count and fraction.

## Primary outcomes

For output `Y_hat`, target truth `Y_target`, and host source-policy action
`Y_source`:

- source-policy adherence: `S=P(Y_hat=Y_source)`;
- target exact accuracy;
- `Gamma_R = S_RS − S_RI` on the high-identifiability subset;
- `Delta_same = Accuracy_RS − Accuracy_RI` on actual SAME_POLICY tasks;
- `Delta_independent = Accuracy_RI − Accuracy_RS` on actual INDEPENDENT_POLICY
  tasks;
- `Upsilon_R = 0.5(Delta_same + Delta_independent)`.

The independent unit is environment seed (`n=4`); prompts/probes are repeated
measurements within seeds. Report all seed values, mean, median, range, and
sample SD. The key distinction is source-policy application versus accidental
target correctness.

## Qualification gates

All thresholds are frozen before inference:

1. `Gamma_R >= 0.10` on high-identifiability tasks and positive in at least 3/4
   seeds;
2. on actual SAME_POLICY tasks, `Accuracy_RS − Accuracy_RI >= 0.10` and RS
   exceeds historical V2 cross-domain accuracy;
3. same tasks/high-identifiability `S_RS >= 0.30`;
4. `Upsilon_R >= 0.10` and positive in at least 3/4 seeds;
5. truthful-R BLOCK geometry has `W>0` and `B>=0.05`;
6. truthful-R geometry has `Q_GLOBAL < Q_BLOCK < Q_DIAGONAL`;
7. directional alignment with exact relation-aware `L*_relation`, not driven by
   one seed.

Classification is **RELATION-CONTROLLED TRANSFER ESTABLISHED** only if all pass;
otherwise **PARTIAL RELATION CONTROL** or **NO RELATION CONTROL**. A new
harness/interface defect is **HARNESS FAILURE**. No classification authorizes a
society.

## Secondary analyses

Compare R0 with historical R_NONE, response entropy/modal output, bitwise effects,
anchoring, semantic pairs, source-identifiability strata, relation-oracle
alignment, and truthful-R transfer matrices. False cues are labeled
counterfactual structural interventions. Do not interpret RS success as natural
ecology inference; it would show only that the learner can condition application
of an inferred source policy on explicit structural information.

## Stopping and interpretation

Freeze manifest, cue strings, task hashes, source actions, identifiability values,
and execution order before any paid call. Stop only for budget, model/backend,
manifest, or data-integrity violation. After 3,456 calls, stop all external
inference. Do not tune cues, add seeds, enable thinking, add factor alignment,
run the bottleneck ladder, or run a society.
