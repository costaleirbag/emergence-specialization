# Response-anchoring audit

**Status: offline descriptive audit; no causal mechanism claim.**

## Corrections to memory-learnability-v1

The previous reliability report grouped by mode/world/k/context seed but omitted
the probe identity. That was wrong: ten distinct held-out tasks were mixed with
three replicates each. The corrected unit is
`mode × world × k × context_seed × probe_id`.

The corrected aggregate reliability is:

| Mode | k | Exact 3-way answer agreement | Pairwise answer agreement | Exact 3-way correctness agreement |
|---|---:|---:|---:|---:|
| same world | 0 | 0.208 | 0.388 | 0.670 |
| same world | 1 | 0.603 | 0.718 | 0.875 |
| same world | 2 | 0.343 | 0.508 | 0.768 |
| same world | 4 | 0.283 | 0.446 | 0.745 |
| same world | 8 | 0.218 | 0.374 | 0.713 |
| unrelated k=8 | 8 | 0.198 | 0.378 | 0.703 |
| wrong prediction + correct feedback | 8 | 0.128 | 0.313 | 0.690 |
| mixed k=8 | 8 | 0.363 | 0.535 | 0.808 |

The old `corrupted_k8` name was misleading. Its records contain a wrong prior
prediction but a truthful `correct_answer`; it is now reported as
`wrong_prediction_with_correct_feedback_k8`. No raw JSONL was altered, and this
arm must not be interpreted as corrupted-label feedback.

## Anchoring definitions

For each response with memory, the audit records whether the answer equals the
last prediction, last feedback label, any feedback label, or modal feedback
label. For empty memory the fields are undefined, not zero. The calibration
report also compares correctness and confidence conditional on last-label
anchoring. These are response-level diagnostics; context/world is the intended
replication unit.

## Clean v2 society observations

At probe checkpoints, last-label and any-label copying increased most strongly
in shared memory. The mean pairwise answer agreement among four agents was:

| Cell | t=0 | t=10 | t=20 |
|---|---:|---:|---:|
| confidence/private | 0.393 | 0.318 | 0.334 |
| confidence/shared | 0.385 | 0.571 | 0.654 |
| random/private | 0.409 | 0.360 | 0.438 |
| random/shared | 0.398 | 0.671 | 0.708 |

This is consistent with common memory producing behavioral synchronization, but
it does not establish that anchoring is the sole cause of HSE/Phi changes. In
the confidence/shared t=20 probe records, last-label anchoring averaged 0.161
and any-label anchoring 0.947; correctness when anchored was 0.218 versus 0.200
when not anchored. Thus copying was common without being a clear competence
advantage.

The complete response-level and probe-level tables are in
`reports/response-anchoring/`. Regenerate with:

```bash
PYTHONPATH=src .venv/bin/python -m emergent_specialization.response_anchoring
```
