# Reproducibility audit — overnight session

## Frozen inputs

- clean v2 campaign: `data/campaigns/developmental-dynamics-v2/campaign.json`
- clean v2 probe hash: `cb234422389ff7d5a04566112a483f147e4a3d1212b1c69fbb0396ec9ca4c55e`
- calibration config: `configs/research/memory_learnability_v1.yaml`
- calibration base config hash: `03c63facce5efb0cad377e9da6f0c5b6b647fe28b296f56c577cb402a133e2a2`
- calibration config hash: `3e6b9f4d6776e28e6a45d68d1d1b38cf6bb0b4a08c51c1114d72fa09d0661b3e`
- provider fingerprint: `fp_a18b46594c_prod0820_fp8_kvcache_20260402`

## Verification

- Tests: **123 passed** with the repository's offline `.venv` interpreter.
- `compileall -q src`: **PASS**.
- Calibration logical coverage: **100%**.
- Calibration physical attempts: **9,669**.
- Calibration observed cost: **US$0.398420**.
- Probe memory mutation: **false by construction and preflight assertion**.
- Hidden-rule leakage: **false by preflight assertion**.

The convenient `uv run` command may attempt an unavailable dependency-index lookup
in a network-isolated environment; the validated fallback is
`PYTHONPATH=src .venv/bin/python`.

## Real-model call audit

- DeepSeek calls: 9,600 authorized calibration completions.
- New society calls: 0.
- OMP calls: 0.
- Bitwarden unlocks: 0.
- Secrets printed: 0.
- External model providers other than DeepSeek Direct: 0.

## Provenance caveat

User-owned untracked files (`Emergent LLM Societies.md`, presentation draft,
and `.DS_Store`) were preserved and not silently modified. Calibration raw data
are intentionally untracked/generated outputs and are not committed as source.
