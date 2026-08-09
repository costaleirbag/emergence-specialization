# Learner response geometry

Treat DeepSeek as a model-specific map `L^m = M(E, q_m, h, representation)`
without assuming linearity or equality between the ecology prior `p_E` and the
pretrained prior `q_m`.

The V1 map is mixed. BLOCK diagonal gain narrowly clears the fixed +0.10
threshold, but within-block transfer is approximately zero and cross-block
transfer is slightly negative. GLOBAL does not show dense positive transfer;
DIAGONAL does not show strong same-niche learning. The realized map therefore
compresses the designed geometry and includes context/prior residuals.

The identity `L^m = alpha L*_obs + R` is descriptive only. `R` is not assumed
to be noise or causally interpreted from four seeds. Possible future diagnostics
(design only) should distinguish semantic parsing, h=8 insufficiency, joint
composition, and generic context/anchoring without revealing family IDs or
using a society as a debugging instrument.
