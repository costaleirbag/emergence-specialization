# Learner Calibration V1 Harness Audit

## Classification

**LEGACY — HARNESS-CONFOUNDED.** V1 remains preserved as historical raw data,
but its transfer metrics must not be interpreted as a clean estimate of DeepSeek
plasticity.

## Static output instruction

The exact V1 instruction was:

```text
Return only JSON: {"decisions":[0,1,0]}. The array must contain exactly three binary decisions in order.
```

This contains a complete valid scientific decision vector. It is therefore a
candidate answer as well as a format instruction.

## Independent raw audit

Audited V1 manifest and all 1,440 terminal raw events.

| quantity | value |
|---|---:|
| `P(output=[0,1,0] | baseline)` | 176/288 = 0.6111 |
| `P(output=[0,1,0] | transfer)` | 1029/1152 = 0.8932 |
| `P(target=[0,1,0])` | 42/288 = 0.1458 |
| `P(memory label=[0,1,0])` | 912/9216 = 0.0990 |
| transfer accuracy when output is `[0,1,0]` | 0.1487 |
| transfer accuracy when output is not `[0,1,0]` | 0.3252 |

The fixed vector became more frequent under transfer while being less accurate,
which makes the V1 transfer gains unusable as evidence for selective learning.

## Probe-input audit

V1 used 30 unique symbolic input states across 288 baseline rows. Marginals were:

| dimension | value 0 | value 1 | value 2 | value 3 |
|---|---:|---:|---:|---:|
| x1 | 144 | 87 | 35 | 22 |
| x2 | 128 | 79 | 47 | 34 |
| x3 | 82 | 87 | 63 | 56 |

The old selector chose the lexicographically first six cases satisfying output
bit balance. It did not balance symbolic inputs. This is a second, independent
evaluation-support confound.

## Consequence

V1 values for D/O/Q/B, learner projection, and residual geometry are legacy
observations only. The correct next step is the harness-neutral V2 calibration:
no concrete vector in static instructions and eight symbolically balanced,
history-disjoint probes selected without using model outputs or target labels.
