# Random-routing mechanism control — preflight

Status: **PASSED — authorized to execute `gate_random_routing_10`**

This document freezes the offline checks performed immediately before the
authorized real control. It does not authorize Gate 2, the original 50-pair
random-routing candidate, long-horizon runs, softmax, locality sweeps, or
interventions.

## Frozen repository state

- Branch: `research/developmental-dynamics`
- Analysis/tooling HEAD before the real control: `8de87c6`
- Gate 1: complete; 20/20 runs complete and logically covered
- Gate 2: locked
- Probe-set SHA-256: `cb234422389ff7d5a04566112a483f147e4a3d1212b1c69fbb0396ec9ca4c55e`
- Probe file SHA-256: `9a68327d639ceadf2164f26307e7ccbacc81a8fb25d4cee7fbc836630f7327aa`

## Test and compile gate

```text
uv run python -m unittest discover -s tests -v  -> 111 tests, all passed
uv run python -m compileall -q src              -> passed
```

The suite includes explicit checks that random-private/shared runs with a
paired seed have identical task sequences and identical random interaction
routing sequences under a deterministic backend. The random router sorts agent
IDs before sampling, consumes one explicit router RNG draw per selection, and
does not inspect confidence.

## Planned design

| field | value |
|---|---|
| gate | `gate_random_routing_10` |
| seeds | 1–10 |
| conditions | private, shared |
| runs | 20 (10 pairs) |
| router | random |
| agents | 4 |
| rounds | 20 |
| checkpoints | `[0, 10, 20]` |
| probes/checkpoint | 40 |
| logical completions/run | 560 |
| logical completions/gate | 11,200 |
| physical-attempt ceiling | 14,000 (20 × 700) |
| hard cost ceiling | US$1.00 |
| expected cost at observed rate | approximately US$0.40350 |
| backend | DeepSeek Direct |
| model | `deepseek-v4-flash` |
| credential source | macOS Keychain, handled by the configured backend |
| OMP | not used |
| Bitwarden | not used |

## Config audit

The random pair differs only in `condition.memory_mode`:

- private config hash: `74aac4293237029f26c87dea023dcabf85b4ee29c77eb2710ed74409fc116b74`
- shared config hash: `4eb4c092c2f5104e1a26a769c160c267386e82db4c242106549c26ab0f5211d5`

Relative to the corresponding confidence configs, the scientific change is
`router.strategy: confidence -> random`. The output directory changes only the
artifact location and is not a scientific parameter. Model, prompt, hidden
worlds, task generation, rounds, checkpoints, probe set, memory policy,
feedback semantics, parser, retries, backend and decoding settings match.

## Pairing invariants

For each seed, the task RNG and router RNG are explicit streams. The same seed
therefore yields the same task sequence for:

```text
confidence-private, confidence-shared,
random-private, random-shared
```

For random-private versus random-shared, the random interaction routing stream
is also identical because random selection is independent of responses,
confidence, memory and asynchronous completion order. Probe routing is an
analysis/checkpoint diagnostic and is not used as an interaction intervention.

## Guard and execution policy

The official campaign runner is the only real execution path. It requires
explicit `--confirm-real`, runs one condition at a time, reuses/resumes exact
identities, and checks both the US$1.00 gate cap and the 14,000 physical-attempt
ceiling before launching work. A failed/incomplete pair blocks continuation;
scientific results never change scheduling.

The exact command used for the authorized run is:

```bash
uv run python -m emergent_specialization.campaign \
  --run-gate gate_random_routing_10 \
  --confirm-real
```

After this gate completes or is blocked, all further work is offline. Gate 2
remains locked.
