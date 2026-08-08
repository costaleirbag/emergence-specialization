# Memory representation × thinking report

**Status: PARTIAL / BLOCKED BY AUTHORIZED COST GUARD.**

## What was completed

The `off` arm completed its planned 16,800 logical queries. The balanced probe
set has 14 probes/world, exactly two for every answer label 0–6, with hash
`7c5370122b553dafbd1ef950f3b4de9ca9636f7c3922cb31800169638b59c2df`.

The same-model DeepSeek V4 thinking toggle is officially supported, but the
thinking arm was not operationally affordable/reliable under this protocol's
US$3 ceiling: at 128 and 512 output tokens reasoning frequently consumed the
entire budget, and at 2,048 tokens many calls still returned only reasoning with
no final JSON. Continuing with a larger cap projected beyond the hard budget, so
the run was stopped as required. This is not evidence that thinking is
scientifically ineffective.

Observed calibration attempts so far:

- 18,031 physical attempts recorded;
- observed token cost approximately US$0.819;
- 16,800 valid `thinking=off` logical completions;
- no complete factorial `thinking=high` arm;
- technical errors: empty content, transient transport, and a few parse errors;
- 113 valid out-of-domain scientific answers in the off arm.

The partial raw dataset is in
`data/calibrations/memory-representation-thinking-v1/`; the balanced probe
manifest is stored alongside it.

The complete off-only balanced-probe curves were:

| Representation | k=0 | k=1 | k=2 | k=4 | k=8 | k8−k0 |
|---|---:|---:|---:|---:|---:|---:|
| full experience | 0.126 | 0.133 | 0.135 | 0.135 | 0.137 | +0.011 |
| feedback only | 0.126 | 0.141 | 0.143 | 0.146 | 0.139 | +0.013 |

These are descriptive balanced-probe means over context seeds and replicates;
they show no strong monotone competence gain. At k=8, feedback-only and full
experience are nearly identical. The truly corrupted feedback control was 0.144
versus 0.139 for correct feedback in the off-only arm, so this partial result
does not show a positive correct-label gain.

## Scientific status

Because the thinking-on cell is incomplete, no representation effect,
thinking effect, or representation × thinking interaction is reported as a
factorial conclusion. The off-only curves and confidence/anchoring diagnostics
are descriptive and should not be pooled with `memory-learnability-v1`.

## Reproducible offline report

```bash
PYTHONPATH=src .venv/bin/python -m emergent_specialization.memory_representation_thinking_report
```

The output is in `reports/calibrations/memory-representation-thinking-v1/`.
