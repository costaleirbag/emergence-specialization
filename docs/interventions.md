# Causal interventions

Interventions operate only on Python-controlled scientific state. They never
modify OMP sessions or provider configuration. A scheduled memory intervention
is applied immediately before its `trigger_round` and emits an `intervention`
event containing operation, agents, selected worlds, and before/after counts and
memory hashes.

Supported memory operations:

- `memory_swap`: exchange two complete memories;
- `memory_erase`: clear one memory (or selected worlds);
- `memory_clone`: copy one complete memory to another;
- `memory_transplant`: copy only experiences from declared worlds.

`PopulationState` provides an explicit, testable scaffold for `ablate_agent`,
`add_naive_agent`, `replace_agent`, and `reintroduce_agent`. The fixed-N
`ExperimentRunner` deliberately does not execute population operations yet,
because existing probe and matrix schemas assume a stable population. This is a
documented boundary, not a silent partial implementation.

## Example

```yaml
interventions:
  - trigger_round: 41
    operation: memory_swap
    source_agent: agent_0
    target_agent: agent_1
```

Recovery helpers measure transparent quantities such as time to cross a
pre-declared performance threshold, best-world competence recovery, and first
replacement routing. They do not select “specialists” automatically.

