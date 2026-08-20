# Minimal Developmental Society V1 — preregistration

Status: frozen before paid inference.

- Provider/model: DeepSeek Direct / `deepseek-v4-flash`, thinking off.
- Geometry: V3.1 DIAGONAL; families: ACCESS, RELEASE, INCIDENT, PROVENANCE.
- Seeds: `27101, 27102, 27103, 27104, 27105, 27106, 27107, 27108`; regimes: RP, AP4, AP12, AS12.
- N=4; T=128; checkpoints `(0, 16, 32, 64, 96, 128)`; recent-k=8.
- Beta prior `(alpha,beta)=(1.0,7.0)`; epsilon=0.1; beta values {'RP': 0.0, 'AP4': 4.0, 'AP12': 12.0, 'AS12': 12.0}.
- Held-out support: 16 X states, four occurrences per level/axis; online tasks use the remaining 48 states, 32 per family in 32 balanced blocks.
- Expected calls: t0 2048, online 4096, post-checkpoints 40960, total 47104.
- Hard external cap: US$2.25; technical retries only, maximum 2 attempts/logical completion.

Primary statistic: `Psi_spec(A)=||P_N A P_K||_F^2/(N K)`, separately for bit and exact-joint competence. Primary comparisons are AP12−RP and AP12−AS12 at t=128 and normalized AUC. `Phi`, matching gain, routing MI, eta, memory/exposure composition, team utility, role persistence, and HSE are secondary.

A valid scientific answer or semantic out-of-domain answer is terminal and is never retried. Empty/malformed/transport/rate-limit/server failures are technical and may be retried. Any missing logical completion, model identity mismatch, manifest mutation, or hard-budget violation stops the campaign. No interventions, extra seeds, extra beta values, GLOBAL/BLOCK, confidence routing, role labels, hidden theta, or post-result adaptation.
