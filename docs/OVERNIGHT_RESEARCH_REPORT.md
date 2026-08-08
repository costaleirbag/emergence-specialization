# Overnight autonomous research report — 2026-08-08

## Executive summary

The clean v2 2×2 campaign remains the frozen society dataset: 40 complete runs,
22,400/22,400 logical completions, US$0.649597, with CLEAN and RECOVERED health
explicitly retained. A separate, pre-authorized single-agent calibration was
completed to test whether the frozen memory/prompt setup is learnable before any
new society campaign.

The calibration completed 9,600/9,600 logical queries at US$0.398420. It found
substantial stochasticity and no monotone same-world accuracy improvement as
`k` increased. Confidence also became poorly calibrated under memory contexts.
This is a protocol-readiness result, not evidence for or against emergent
specialization.

## What was executed

- One authorized `memory-learnability-v1` calibration only.
- DeepSeek Direct, `deepseek-v4-flash`, Keychain credential source, no OMP.
- No new society run, no Stage B/Gate 2, no long-horizon run, no intervention,
  topology, model, prompt, or hidden-world change.
- No API key, Bitwarden secret, or credential value was printed or persisted.

## Reproducibility

Calibration preflight was committed at `86a8fce` on top of clean-v2 report HEAD
`e85a3fd`. The calibration manifest records config hash, base-config hash, probe
hash, system-prompt hash in events, provider model/fingerprint, attempt count,
usage, and cost. Raw events are append-only and duplicate-safe by query ID.

## Scientific interpretation boundary

The clean v2 endpoints are descriptive: confidence/private increased mean HSE
from 0.4715 to 0.5548 and Phi from 0.00927 to 0.01002, while
confidence/shared decreased HSE from 0.5271 to 0.2873 and Phi from 0.00780 to
0.00469. Random/private and random/shared provide a router control. These
contrasts remain compatible with several mechanisms and are not causal claims.
The calibration makes a separate point: current memory exposure alone should not
be assumed to generate reliable task competence.

## Next decision (human review required)

Before any new paid society campaign, choose explicitly between:

1. freeze clean v2 as a developmental-dynamics study and analyse its existing
   evidence without claiming learnability; or
2. register a new protocol that first fixes/validates learnability, with new
   configs, hashes, and a separate campaign identity.

No next scientific experiment was started automatically.
