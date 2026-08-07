# DeepSeek Direct concurrency benchmark

> **INFRASTRUCTURE BENCHMARK — NOT SCIENTIFIC DATA**

Run at `2026-08-07T21:53:26Z` with `deepseek-v4-flash`, thinking disabled,
JSON Output, one long-lived direct client, and 32 probe-like jobs per level.
The benchmark used one physical attempt per job (no benchmark retries), a total
physical ceiling of 128, and a total cost ceiling of USD 0.25.

| concurrency | success | attempts | retries | 429 | 5xx | timeouts | req/s | p50 (s) | p95 (s) | p99 (s) | cost (USD) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4  | 32/32 | 32 | 0 | 0 | 0 | 0 | 3.633 | 0.968 | 1.236 | 1.560 | 0.00040768 |
| 8  | 32/32 | 32 | 0 | 0 | 0 | 0 | 7.607 | 0.915 | 1.183 | 1.240 | 0.00040768 |
| 16 | 32/32 | 32 | 0 | 0 | 0 | 0 | 15.332 | 0.924 | 1.018 | 1.092 | 0.00040768 |
| 32 | 32/32 | 32 | 0 | 0 | 0 | 0 | 23.097 | 1.035 | 1.333 | 1.357 | 0.00040768 |

Total observed cost: **USD 0.00163072**. Cache hit ratio was **0.0** at all
levels (0 hit / 8,064 input tokens; 8,064 misses). The benchmark deliberately
used separate level namespaces, so this does not test warm-cache reuse.

Throughput relative to concurrency 4 was 1.00×, 2.09×, 4.22×, and 6.36×.
There was no observed HTTP 429, 500/503, transport error, timeout, or retry.
The p95 latency did not show an explosive knee at 32; therefore the conservative
freeze is:

```text
RECOMMENDED_PROBE_CONCURRENCY = 32
```

Both replication configs were changed identically from 16 to 32. Interaction
concurrency remains 4. No scientific prompt, memory, router, task, checkpoint,
or metric was changed.

Raw machine-readable artifact:

`reports/infrastructure-benchmarks/benchmark.json`

The benchmark remains infrastructure-only and must not be interpreted as a
scientific result.
