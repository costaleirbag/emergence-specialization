# TRANSFER-GEOMETRY-CONTROL-V1 preregistration

Frozen before paid inference. This is a single-agent calibration, not a
society experiment. Model: `deepseek-v4-flash`, DeepSeek Direct, thinking off;
five paired environment seeds (8101–8105), four canonical OPE families, eight
balanced held-out probes/family, two stateless provider replicates.

## Conditions

- **GLOBAL:** two of three substantive factors shared by every family; one
  family-specific factor.
- **BLOCK:** ACCESS/RELEASE share two factors and INCIDENT/PROVENANCE share two;
  cross-block substantive factors are independent; one unique factor/family.
- **DIAGONAL:** all three substantive factors are family-unique.

Shared factors tie the same run-specific parameter/value. Generic grammar is
not counted in `S` or `G`.

## Frozen streams and calls

For each geometry/seed/source, eight natural cases are ordinary train-pool
samples and eight teaching cases use the exact greedy information criterion;
`h=4` is their first four. Foreign-theta uses the next seed cyclically and the
same semantic family. Baselines are one empty-memory prompt per probe; no
duplicate paid calls are made for identical baseline prompts.

Expected calls: baseline 960; natural h=8 full matrix 3,840; teaching h=8 full
matrix 3,840; natural h=4 diagonal 960; teaching h=4 diagonal 960;
foreign-theta h=8 diagonal 960; total **11,520 logical completions**.

## Qualitative predictions

1. GLOBAL has denser off-diagonal transfer, lower `Q`, and weaker centered
   contrast energy than DIAGONAL.
2. DIAGONAL has larger `Q` and stronger niche-contrast structure than GLOBAL.
3. BLOCK has within-block off-diagonal transfer above cross-block transfer and
   a positive block-mode Rayleigh quotient.
4. Empirical `L` aligns positively with designed `G`, at least under teaching;
   natural alignment may be weaker.
5. Teaching diagonal learning is at least as large as natural learning on
   average, without requiring every seed to obey.
6. Same-theta diagonal performance exceeds foreign-theta performance if
   environment-specific procedure is learned.
7. Centered spectra differ qualitatively across geometries.

No significance claim, adaptive redesign, additional seed, society run, or Gate
2 is authorized by this document.
