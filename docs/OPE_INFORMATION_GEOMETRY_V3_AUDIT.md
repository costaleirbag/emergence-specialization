# OPE information geometry V3 audit

The executable instrument is `src/emergent_specialization/ecological_information.py`.
It contains no provider imports and is safe to run offline.

The audit writes `v3_G.csv`, `v3_J_Lstar.csv`, and
`v3_geometry_summary.csv`, plus the retrospective V2 tables. It records the
Monte Carlo draw count in `v3_manifest.json`.

The primary estimands are natural-history `J` and `L*`; teaching is a positive
control only. `D`, `O`, and `Q=D-O` summarize diagonal, off-diagonal, and
locality information. `W` and `C` are within- and cross-block off-diagonal
information for BLOCK. Analytically independent cells are expected to be zero;
finite estimates are not treated as causal evidence.

The executed run used 2,000 deterministic draws per cell (the 10,000 target was
locally prohibitive and the protocol minimum is 2,000). All gates A--H are
`PASS` in `v3_gates.csv`; the exact independent-cell checks are zero rather
than Monte Carlo approximations. Natural h=8 `Q_J` is 0.0000, 0.6607, and
0.9913 for GLOBAL, BLOCK, and DIAGONAL respectively, while `Q_L*` is 0.0000,
0.5744, and 0.8620. These are ecology-level Bayes diagnostics only.

The report classifies the gates as PASS, FAIL, or NOT-DECISIVE and keeps the
construct-validity caveats visible: the V3 ecology is synthetic, the prior is
chosen by the instrument, and a Bayes result is not a pretrained-LLM result.
