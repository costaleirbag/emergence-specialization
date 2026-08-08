# Offline robustness notes

The existing clean-v2 report retains the fixed 40-probe checkpoint metrics and
the full seed-paired endpoint table. The overnight audit adds endpoint deltas,
paired private-minus-shared contrasts, and leave-one-seed-out (jackknife)
tables in `reports/overnight/`.

Probe subsampling/jackknife over individual probes was not substituted for the
primary fixed-probe metrics: the checkpoint artifacts do not retain enough
per-probe linkage in the aggregate CSV to perform that resampling without
re-reading every raw run. This is a clearly identified offline TODO, not a
scientific result. No primary metric was changed.
