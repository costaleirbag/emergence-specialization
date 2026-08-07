# Minimal non-LLM model

`emergent_specialization.minimal_model` is a dependency-free sandbox for
mechanism checks. It maintains a skill matrix `skill[agent, task]`, selects a
task-dependent agent with a softmax policy plus optional exploration, samples a
correctness outcome from the selected skill, and updates either the selected
agent or the broadcast population according to `private_probability`.

It is not fitted to DeepSeek outputs, is not a scientific result, and should not
be used to justify a phase-transition claim. Its value is that a proposed
feedback mechanism can be inspected deterministically before spending model
calls.

```python
from emergent_specialization.minimal_model import MinimalModelConfig, simulate

result = simulate(MinimalModelConfig(rounds=40, private_probability=1.0, seed=1))
print(result.final_skills)
```

