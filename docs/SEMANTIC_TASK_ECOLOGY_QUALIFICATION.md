# Semantic task ecology qualification

This phase measures **single-agent learning-transfer geometry**, not roles,
specialization, or division of labor.

For source niche `c`, target niche `d`, and horizon `h`:

`L_cd(h) = A_d(E_c^h) - A_d(0)`.

The primary replication unit is environment seed. Each candidate uses five
predeclared seeds, eight held-out probes per target niche, two provider
replicates, a no-memory baseline, the full h=8 source/target matrix, and the
nested h=4 diagonal.

Qualification thresholds are fixed:

- `D >= +0.10` mean diagonal gain;
- `Q = D - O >= +0.07` comparative-advantage/locality index;
- at least three of four niche-specific `q_c > +0.05`;
- no leakage/imbalance explanation and no single-seed domination.

The labels are `MODEL-NONLEARNABLE`, `LEARNABLE-BUT-GENERAL`,
`STRUCTURED-TRANSFER`, or `PROMISING SPECIALIZATION SUBSTRATE`. The last label
still does not mean specialization occurred. Any candidate failing offline
qualification receives zero paid calls.

## Qualification execution result

Both candidates passed the deterministic offline generator/verifier gate over
800 ecology/family/seed rows (100 environment seeds per ecology). The paid
qualification used exactly five predeclared environment seeds, 1,920 logical
contexts per candidate, two provider replicates, no-memory baselines, the full
h=8 matrix, and the nested h=4 diagonal.

| candidate | baseline accuracy | D | O | Q | q_c (ACCESS, INCIDENT, PROVENANCE, RELEASE) | classification |
|---|---:|---:|---:|---:|---|---|
| OPE | 0.4188 | 0.1313 | 0.0323 | 0.0990 | 0.2125, 0.0500, 0.0792, 0.0542 | PROMISING SPECIALIZATION SUBSTRATE |
| CWDE | 0.2250 | 0.1344 | 0.0427 | 0.0917 | 0.0917, 0.2167, 0.1125, -0.0542 | PROMISING SPECIALIZATION SUBSTRATE |

For OPE, the preregistered within-block minus cross-block statistic was
`B_OPE = 0.0125`. Both candidates satisfy the descriptive D/Q/q thresholds;
this is evidence about **single-agent learning-transfer geometry**, not a claim
that roles, specialization, or division of labor emerged. Per-seed tables and
response-level records are retained under `reports/task-ecology/qualification-v1/ope/`
and `.../cwde/`.

OPE had one semantic out-of-domain response and CWDE had four; none were
retried, and all were retained as incorrect completed logical observations.
Both candidates had 1,920/1,920 logical coverage and zero technical retries.
