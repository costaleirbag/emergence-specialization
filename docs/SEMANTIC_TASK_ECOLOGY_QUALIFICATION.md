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

