# Cross-Domain Transfer Bottleneck V1

**Frozen single-agent diagnostic; no society run.**

## Question

What prevents cross-domain transfer after relation information is supplied? The
diagnostic separates source-policy induction, semantic correspondence, canonical
representation, target semantic parsing, and execution.

## Frozen data and model

- DeepSeek Direct, `deepseek-v4-flash`, thinking off.
- Exact V2 natural h=8 histories and eight held-out probes.
- Environment seeds 9201–9204, geometries GLOBAL/BLOCK/DIAGONAL.
- New cross-domain population: only true-SAME_POLICY tasks (512 total: 384
  GLOBAL and 128 BLOCK). DIAGONAL contributes no cross-domain same-policy cells.
- Local reference: 384 same-family source tasks from the same V2 manifest.
- New logical calls: 384 LOCAL_REP + 5×512 cross = **2,944**.
- Existing V2 and Relation-Signal observations are historical references; they
  are not rerun.

## Ladder

1. `LOCAL_REP`: same-family semantic source policy, no relation cue.
2. `A0_RELATION_ONLY`: true-SAME cross-domain with the old RS relation cue.
3. `A1_SEMANTIC_PI`: A0 plus explicit deterministic semantic correspondence
   between the three source/target attributes and their four states.
4. `A2_CANONICAL`: A0 with canonical dimension/state rendering for history and
   target.
5. `A3_RULE_SEMANTIC`: true policy table supplied in target semantic labels;
   semantic target still requires parsing.
6. `A4_RULE_CANONICAL`: true policy table supplied in canonical states;
   target execution and three-bit JSON composition remain.

A3/A4 are privileged positive controls. They do not establish spontaneous
ontology discovery or natural rule induction.

## Primary metrics and gates

The primary outcome is exact three-bit joint accuracy; component accuracies are
secondary. Define:

```text
Gap_cross = A_LOCAL - A0
Delta_Pi = A1 - A0
Delta_canonical = A2 - A1
Gap_induction_canonical = A4 - A2
Gap_target_semantics = A4 - A3
```

The ontology-alignment gate is `Delta_Pi >= .10`, positive for at least 3/4
seeds, and `A1 >= .25`. Diagnostic thresholds are fixed: strong induction gap
`> .25`, strong target-semantic gap `> .15`, and execution concern when
`A4 < .75`. These are engineering diagnostics, not powered significance tests.

## Secondary analyses

Use contemporaneous LOCAL_REP responses to calculate model-response transport and
stratify A0/A1/A2 by local source success. Also stratify by host `A*_source >=
.99`, report semantic pairs, component metrics, output distributions, and
memory anchoring. Responses are repeated measurements; seed is the scientific
replication unit.

## Leakage and retries

No prompt may include geometry, theta, seed, family ID, or an explicit current
answer vector. A3/A4 may include rule tables but not the final vector as an
explicit string. Valid wrong/OOD outputs are terminal scientific observations;
only malformed, empty, transport, or server failures may retry once.

## Interpretation boundary

If A1 succeeds, conclude only that explicit semantic alignment enables policy
reuse; do not claim spontaneous analogy discovery. If A2 succeeds while A1
fails, representation is implicated. If A4 is low, the substrate cannot reliably
execute even privileged policy tables. No outcome authorizes a society.
