# Next gate after regime observability audit

**Design only. No inference executed.**

The recommended next gate is **Relation-Signaled Cross-Domain Transfer V1**.
Reuse the frozen V2 model, seeds, natural h=8 histories, evaluation probes, and
single-completion policy. Add one predeclared natural-language statement to each
cross-domain prompt indicating only whether the source and target domains share
an underlying decision policy:

- `SAME_POLICY`: the corresponding operational attributes use the same hidden
  policy;
- `INDEPENDENT_POLICY`: the policies are generated independently.

Do not reveal geometry names, theta values, canonical factor IDs, or the policy
mapping. Same-family prompts should remain unchanged unless the reviewed design
explicitly requires a matched neutral statement.

## Why this gate

The relation-aware exact oracle reproduces the full-regime Bayes opportunity in
the current finite ecology, while requiring strictly less privileged information.
The intervention therefore tests whether the missing structural prior explains
the weak V2 cross-domain transfer. It does not test natural regime inference and
may make transfer artificially easier; that is why it is a positive-control gate,
not the final developmental experiment.

## Alternatives retained

- **Known ecology:** expose the full sharing structure as a stronger synthetic
  positive control.
- **Hidden but inferable ecology:** provide multi-family evidence and measure
  joint learning of policies and `G`.
- **Hidden/unidentifiable ecology:** retain V2 to study the model's spontaneous
  prior `q_m(G)`.

The principal researcher should choose among these after reviewing the offline
audit. No choice is executed automatically, and the society gate remains closed.
