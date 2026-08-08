# Response semantics audit

> Offline audit of legacy real-run inference events. This document does not modify raw artifacts and makes no new model calls.

## Classification

The audit distinguishes transport/provider failures, malformed/unreadable output, semantic answer-domain violations, confidence-domain violations and other errors. A valid JSON object with an integer answer outside `[0,6]` and confidence inside `[0,1]` is classified as a scientific answer-domain violation, even though legacy runs logged it as a parse error.

### A. Transport/provider failures

- count: **24**
- by phase: `{'probe': 20, 'round': 4}`
- by condition: `{'shared': 17, 'private': 7}`
- by router: `{'confidence': 21, 'random': 3}`
- first attempts: **24**
- events whose logical completion eventually succeeded via old retry: **24**
- selected interaction candidates: **0**

### B. Malformed/unreadable model output

- count: **7**
- by phase: `{'probe': 5, 'round': 2}`
- by condition: `{'private': 1, 'shared': 6}`
- by router: `{'confidence': 7}`
- first attempts: **7**
- events whose logical completion eventually succeeded via old retry: **7**
- selected interaction candidates: **0**

### C. Semantic answer-domain violations

- count: **26**
- by phase: `{'probe': 22, 'round': 4}`
- by condition: `{'shared': 9, 'private': 17}`
- by router: `{'confidence': 18, 'random': 8}`
- first attempts: **25**
- events whose logical completion eventually succeeded via old retry: **24**
- selected interaction candidates: **2**

### D. Confidence-domain violations

- count: **0**
- by phase: `{}`
- by condition: `{}`
- by router: `{}`
- first attempts: **0**
- events whose logical completion eventually succeeded via old retry: **0**
- selected interaction candidates: **0**

### E. Other

- count: **0**
- by phase: `{}`
- by condition: `{}`
- by router: `{}`
- first attempts: **0**
- events whose logical completion eventually succeeded via old retry: **0**
- selected interaction candidates: **0**

## Key consequence

The old parser treated answer-domain violations as retryable technical failures. Probe-only cases affect measurement but can be sensitivity-scored offline. Interaction cases can change the selected candidate, stored `Experience.prediction`, memory state and all later trajectory; they cannot be exactly repaired offline. Therefore the old Gate 1 and random-v1 artifacts remain LEGACY / EXPLORATORY evidence.

The complete event-level table is `docs/response_semantics_audit.csv`; raw run directories remain unchanged.
