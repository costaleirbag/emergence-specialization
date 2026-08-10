# Local Plasticity Curve V1 — Preregistration

**Status:** frozen microscopic gate; no society, routing, or Gate 2.

## Question

Does h resolved natural experience from a target niche improve exact joint
competence on that niche more than equally sized resolved experience from an
independent foreign niche?

For target niche `c`:

```text
A0             = accuracy after empty memory
A_same(h)      = accuracy after h natural cases from c
A_foreign(h)   = accuracy after h natural cases from d != c
G_abs(h)       = A_same(h) - A0
G_rel(h)       = A_same(h) - A_foreign(h)
G_foreign(h)   = A_foreign(h) - A0
```

The minimal substrate requires useful absolute and relative plasticity. A
positive relative gain caused only by foreign-context harm is insufficient.

## Frozen substrate

- ecology: V3.1 `DIAGONAL` only;
- seeds: 9201, 9202, 9203, 9204;
- niches: ACCESS, INCIDENT, PROVENANCE, RELEASE;
- histories: exact corrected V2 natural h=8 histories, original order;
- horizons: h ∈ {1, 2, 4, 8}, strict prefixes;
- probes: exact V2 eight balanced, history-disjoint evaluation probes;
- output: corrected neutral V2 JSON schema, exact three-bit joint correctness;
- model: DeepSeek Direct `deepseek-v4-flash`, thinking off;
- provider replicates: one completion per exact prompt;
- primary scientific unit: environment seed (n=4).

No relation cue, correspondence, canonicalization, explicit rule, teaching
history, GLOBAL/BLOCK geometry, or society is included.

## Logical calls

| condition | calls |
|---|---:|
| EMPTY | 4×4×8 = 128 |
| SAME(h), four horizons | 4×4×8×4 = 512 |
| FOREIGN(d→c,h), all three foreign sources | 4×4×3×8×4 = 1,536 |
| **total** | **2,176** |

Conditions are deterministically interleaved before execution.

## Gates

- **L1:** `G_abs(8) ≥ .10` and positive in ≥3/4 seeds;
- **L2:** `G_rel(8) ≥ .10` and positive in ≥3/4 seeds;
- **L3:** integrated `I_abs = mean_h G_abs(h) ≥ .05` and positive in ≥3/4 seeds;
- **L4:** integrated `I_rel = mean_h G_rel(h) ≥ .05` and positive in ≥3/4 seeds;
- **L5:** aggregate `A_same(8)>A_same(1)` and positive log-dose slope in ≥3/4
  seeds;
- **L6:** all three component-level h8 `G_abs` values positive and ≥2/3 at
  least .05.

All gates are descriptive qualification thresholds, not significance claims.
If all pass, the result is `LOCAL PLASTICITY QUALIFIED`; mixed positive results
are `PARTIAL`; weak or non-selective learning is `NOT QUALIFIED`.

## Bayes reference

Exact prompt-level Bayes opportunity is recomputed from the frozen ecology for
every task. In DIAGONAL, FOREIGN histories must have `A*_foreign=.125` exactly
up to numerical precision. The Bayes curve is descriptive and is not a gate on
model efficiency.

## Retry and integrity rules

Valid but wrong JSON is a terminal incorrect observation. Valid JSON with an
invalid decision domain is terminal semantic OOD and is not retried. Only
malformed, empty, transport, or provider failures may receive bounded technical
retry. The hard new external-inference cap is US$0.12, including retries.

## Non-goals

This preregistration does not test specialization, routing, feedback locality,
symmetry breaking, HSE, MI, or any society-level outcome. No result authorizes a
society automatically; principal-researcher review is required.
