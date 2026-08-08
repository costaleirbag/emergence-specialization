# Gate 1 semantic-retry impact

> LEGACY / EXPLORATORY impact analysis. Raw artifacts are immutable; this is an offline sensitivity audit.

- Semantic answer-domain events: **18**
- Interaction semantic events: **2**
- Probe semantic events: **16**
- Interaction events that were selected candidates under the old retry-resolved trajectory: **1**
- Semantic events whose old logical completion eventually succeeded on retry: **18**

Gate 1's original 10 paired seeds are complete under legacy retry semantics, but interaction out-of-domain first attempts occurred in at least private seed 8 round 2 and private seed 9 round 14. The old Gate 1 remains useful exploratory history, not clean confirmatory evidence.

The event-level details are in `docs/response_semantics_audit.csv`. Probe-only cases can be scored as incorrect without replaying the model. Interaction cases cannot be exactly reconstructed because the old retry response may have changed memory and routing.
