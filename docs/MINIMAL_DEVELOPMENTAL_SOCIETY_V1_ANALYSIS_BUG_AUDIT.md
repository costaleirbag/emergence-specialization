# Minimal Developmental Society V1 — analysis bug audit

## Finding

The paid experiment is **valid** and the original offline competence analysis was
**invalid but repairable**. In `analyze()` the `vals_joint` and `vals_bits`
accumulators were initialized once per agent, outside the niche loop. Each later
niche therefore included prior-niche observations while still dividing by 16
probes (or 48 bit decisions). This is the direct cause of accuracy values greater
than one.

## Forensic counts

- Original `competence_joint.csv`: 158 values > 1; maximum 1.5625; rows 3072.
- Original `competence_bit.csv`: 2177 values > 1; maximum 2.8541666666666665; rows 3072.
- Corrected joint values >1/<0: 0/0.
- Corrected bit values >1/<0: 0/0.

Representative impossible rows are preserved in `reports/society/minimal-developmental-society-v1/original-analysis-invalid/`.

## Impact

The bug corrupts every metric consuming held-out competence matrices: Psi_spec,
Phi, matching gain, role assignments/persistence, competence-aligned routing, and
role-label symmetry. Metrics computed directly from raw online events—routing MI,
online utility, exposure/memory composition, technical health, and cost—are
independent and were recomputed or verified unchanged. See `bug_impact_table.csv`.

## Repair validation

Two independent raw-event aggregations (explicit grouped lookup and event-pivot
reconstruction) agree exactly for 3072 cells.
Every cell has 16 probes and 48 bit decisions. Hungarian and exhaustive 4! role
assignment optima agree for 192 matrices.

The raw event log, frozen manifest, preregistration, run status, and budget hashes
are recorded in `raw_integrity.json` and remained unchanged. No model call was
made and no paid data were regenerated.
