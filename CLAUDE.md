# Codex project instructions

## Research orchestration

This project uses a shallow hierarchical research workflow.

The primary Codex session is the scientific orchestrator running on Sol. It owns:

- hypothesis generation and the hypothesis ledger;
- experimental design;
- causal interpretation;
- experiment prioritization;
- scientific stopping decisions;
- theory integration;
- final conclusions.

Delegate bounded, execution-heavy work to the project-scoped Luna agents:

- `luna_explorer`: repository, data, config, log, and artifact exploration;
- `luna_analyst`: statistics, raw-data computation, recomputation, plots, simulations, and bounded mathematics;
- `luna_implementer`: implementation of already-frozen designs, tests, manifests, and targeted fixes;
- `luna_reviewer`: independent adversarial review and attempted falsification.

For high-impact empirical claims, prefer:

1. one worker computing the result;
2. a separate worker independently validating it;
3. parent scientific synthesis.

Do not delegate final scientific judgment. Do not spawn agents merely to increase parallelism. Prefer the shallow hierarchy `parent -> worker` and return compact evidence summaries rather than large raw dumps.
