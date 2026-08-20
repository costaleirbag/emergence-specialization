# Memory learnability v1 preflight

**Status:** approved for the one authorized real calibration only. This is a
single-agent calibration, not a society run and not a Gate 2 experiment.

## Frozen environment

- Protocol: `memory-learnability-v1`
- Base config: `configs/research/v2/clean_confidence_private_20.yaml`
- Backend: DeepSeek Direct
- Model: `deepseek-v4-flash`
- Thinking: disabled
- System prompt, task rendering, memory rendering and corrected parser reused
  from clean v2
- Worlds: `ALPHA`, `BETA`, `GAMMA`, `DELTA`
- Rules remain experimenter-side only; no formula is put in a model prompt
- Probe set hash: `cb234422389ff7d5a04566112a483f147e4a3d1212b1c69fbb0396ec9ca4c55e`

## Design checks

- `k = [0, 1, 2, 4, 8]`
- 10 deterministic context seeds per world
- 10 held-out probes per target world
- 3 independent calls per identical context/probe query
- Correct teacher examples are synthetic positive controls, not society data
- Corrupted labels are deterministically wrong and use the same inputs as correct contexts
- Unrelated control has zero target-world examples
- Mixed control has exactly 2 examples from each of the 4 worlds
- Exemplar inputs are disjoint from held-out probes
- Probes never update memory
- No router, adaptive feedback, or multi-agent state exists in this calibration
- Replicate IDs are part of the logical query identity; equal prompts are not deduplicated
- Out-of-domain integer answers are completed scientific responses and are not retried

## Call and budget forecast

| Component | Logical queries |
|---|---:|
| Same-world `k=0,1,2,4,8` | 6,000 |
| Corrupted `k=8` | 1,200 |
| Unrelated `k=8` | 1,200 |
| Mixed `k=8` | 1,200 |
| **Total** | **9,600** |

Using the observed clean-v2 token-cost distribution stratified by rendered
memory size, the forecast is approximately **US$0.3715**, below the hard
overnight ceiling of **US$1.00**. The runner also enforces 19,200 physical
attempts and duplicate-safe resume.

## Real execution command

```bash
PYTHONPATH=src .venv/bin/python -m emergent_specialization.memory_learnability \
  --run --config configs/research/memory_learnability_v1.yaml --confirm-real
```

The command above is the only new paid experiment authorized by the overnight
protocol. After it completes or becomes blocked, no further real model calls
are permitted in this session.

## Artifacts

The runner writes `manifest.json` and append-only `events.jsonl` under
`data/calibrations/memory-learnability-v1/`. It can be resumed with the same
command; successful logical query IDs are not called again.
