# Random-v1 semantic-retry impact

> LEGACY / EXPLORATORY impact analysis. Raw artifacts are immutable; this is an offline sensitivity audit.

- Semantic answer-domain events: **8**
- Interaction semantic events: **2**
- Probe semantic events: **6**
- Interaction events that were selected candidates under the old retry-resolved trajectory: **1**
- Semantic events whose old logical completion eventually succeeded on retry: **6**

Random-v1 seeds 1–2 completed under legacy retry semantics; private seed 3 is invalid/incomplete. Its interaction seed-3 round-10 out-of-domain first attempt was retried and the retry response became the selected candidate, so this artifact must not be mixed with the corrected protocol.

The event-level details are in `docs/response_semantics_audit.csv`. Probe-only cases can be scored as incorrect without replaying the model. Interaction cases cannot be exactly reconstructed because the old retry response may have changed memory and routing.
