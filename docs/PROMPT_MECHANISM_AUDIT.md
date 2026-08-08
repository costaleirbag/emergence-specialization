# Prompt mechanism audit

**Status:** read-only audit of executed code and raw artifacts. Prompt changes are
experimental interventions; this document does not alter the clean-v2 baseline.

## What the model sees

The society system prompt says that all worlds obey stable, initially unknown
rules and asks the model to use prior tasks and feedback. It does not insert an
agent ID or persona. The rendered user message is ordered as:

1. controlled-memory preamble;
2. `CONTROLLED_MEMORY_JSON`;
3. `CURRENT_TASK` with world, `x`, `y`, and choices 0--6;
4. the JSON-only response contract.

DeepSeek Direct also requests `response_format={"type":"json_object"}`. The
task and memory never expose `(a,b,c)` or the environment formula.

The prompt says that rules are stable and every record carries a world label,
but it does not state unambiguously that **each world has a distinct rule**. A
model could incorrectly pool examples across worlds. This is a limitation of
the frozen prompt, not a reason to silently rewrite it.

## Memory salience and ordering

`recent_k` retains the last `k` experiences in chronological order. The newest
record is therefore physically closest to the current task. A full Experience
record contains:

- world, `x`, and `y`;
- historical `prediction` and `confidence`;
- truthful `correct_answer` supplied by Python;
- `was_correct` and round ID.

The prompt calls this “controlled feedback memory”, but it never explicitly
says to ignore the previous prediction and privilege `correct_answer`. Both are
plausible anchors. Within the deterministic JSON serialization,
`correct_answer` appears before `prediction`, while the latest record as a whole
is closest to the current task.

## Calibration renderers

- `memory-learnability-v1` reuses the full society Experience renderer. Its
  historical `corrupted_k8` arm changes the prior prediction but preserves true
  feedback. It is an incorrect-prediction-plus-corrective-feedback control, not
  corrupted feedback.
- `memory-representation-thinking-v1/full_experience` uses the same scientific
  fields.
- `feedback_only` retains only world, `x`, `y`, and `correct_answer`; it removes
  prediction, confidence, correctness, and round ID.
- `truly_corrupted_feedback` shifts the visible `correct_answer` by one modulo
  seven. This shift is systematic and itself defines a coherent wrong affine
  rule with intercept `c+1`.

Neither calibration updates memory during probes. They are controlled
single-agent measurements, not society dynamics.

## Existing-data observations

- Clean v2 contains 2,244 exact repeated ordered-context groups involving
  15,283 responses. Only 896 groups had unanimous answers, showing substantial
  sampling variability under identical prompts.
- In the original learnability calibration, `k=1` answers equal the sole/last
  feedback label in 78.6% of 1,200 responses. At `k=4` the rate is 32.0%; at
  `k=8`, 21.8%.
- In the balanced thinking-off calibration, `k=1` last-label matching is 29.5%
  for full experience and 35.1% for feedback-only. At larger `k`, modal-label
  matching can exceed last-label matching, so a pure recency-only story is too
  simple.
- Shared clean-v2 agents have more memory and greater label-set coverage than
  private agents. Any-label overlap is therefore mechanically easier in shared
  memory and must be compared with a coverage-aware null.

These are observations. They do not identify whether the model copies a label,
infers a rule, follows the empirical label distribution, or combines those
processes.

## Causal design implication

The cleanest next anchoring test keeps the memory multiset, size, labels, and
prompt length fixed and changes only deterministic order: original, reversed,
and a prespecified shuffle. Contexts must be rank-full over GF(7), probes must be
disjoint modulo seven, and order must be counterbalanced. Primary analysis must
separate:

- coefficient recovery / held-out competence;
- answer changes across order variants;
- last-feedback and last-prediction matching;
- modal-label matching;
- expected matching from the visible label-set and answer marginals.

The private/shared society contrast cannot by itself isolate this mechanism,
because information locality, per-agent memory volume, memory age, and context
identity all differ.

