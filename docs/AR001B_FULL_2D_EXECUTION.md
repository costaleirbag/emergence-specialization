# AR-001B — full 2D explicit GF(7) execution

AR-001B closes a design flaw in AR-001: the old 56 probes all had `x=0`. The new
manifest has 56 probes, 14 per world, exactly two per answer label, no old probe
coordinate reuse, and both coordinates nonzero for all probes.

The correct affine rule is explicitly shown to DeepSeek V4 Flash. This remains a
single-agent diagnostic, not an induction or society experiment.

Protocol:

- DeepSeek Direct, `deepseek-v4-flash`, thinking off;
- 56 exact probes x 2 stochastic replicates = 112 logical calls;
- valid wrong answers are scientific data and are not retried;
- only transport, empty, or malformed responses may receive one technical retry;
- primary outcome: exact answer accuracy;
- thresholds frozen before execution: >=0.85 strongly weakens arithmetic
  execution as the dominant bottleneck; 0.70--0.85 means imperfect execution;
  <0.70 means a serious execution substrate problem.

The probe hash and raw result are recorded after execution in this document's
corresponding report directory. No follow-up or society run is authorized based
on the outcome.

## Observed result

- status: completed
- logical/physical calls: 112 / 112
- technical retries: 0; errors: 0
- two-dimensional coverage: 56/56 probes had `x != 0` and `y != 0`
- exact answer accuracy: `38/112 = 0.3393`
- usage: 11,088 input tokens, 1,459 output tokens, 12,547 total; 100% usage
  coverage; configured-price estimate US$0.00196084

The pre-registered interpretation is **accuracy < 0.70: serious arithmetic
execution substrate problem**. This is a diagnostic result only. It does not
measure single-agent transfer or society-level specialization, and it did not
change the frozen ecology qualification protocol.
