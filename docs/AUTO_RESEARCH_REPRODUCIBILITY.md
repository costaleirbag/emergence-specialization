# Auto-research reproducibility

## Environment and code

- Branch: `research/developmental-dynamics`
- AR-001 execution HEAD: `96ea83f4b133225f30e704efd95c81fded8a6fd5`
- Python: project `.venv` through `PYTHONPATH=src`
- Model/provider for the only new paid experiment: DeepSeek Direct,
  `deepseek-v4-flash`, thinking off

## Offline verification

From the repository root:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
PYTHONPATH=src .venv/bin/python -m compileall -q src
```

Regenerate exact identifiability, alias/exposure, and HSE sensitivity outputs:

```bash
PYTHONPATH=src .venv/bin/python -m emergent_specialization.hidden_rule_identifiability
PYTHONPATH=src .venv/bin/python -m emergent_specialization.alias_anchor_reanalysis
PYTHONPATH=src .venv/bin/python -m emergent_specialization.hse_robustness
```

Regenerate the AR-001 report from immutable raw events without model calls:

```bash
PYTHONPATH=src .venv/bin/python -m emergent_specialization.explicit_rule_execution --report
```

Do **not** add `--run --confirm-real`: AR-001 is complete and its manifest is
terminal. The documented next ecology screen is not implemented or authorized.

## Authoritative artifacts

- AR-001 raw: `data/auto-research/explicit-rule-execution-v1/events.jsonl`
- AR-001 manifest: `data/auto-research/explicit-rule-execution-v1/manifest.json`
- Zero-call boundary manifest:
  `data/auto-research/explicit-rule-execution-v1-precall-failure-20260808T140745Z/manifest.json`
- AR-001 derived report:
  `reports/auto-research/explicit-rule-execution-v1/report.json`
- Session ledger: `reports/auto-research/cost_ledger.csv`
- GF(7) audit: `reports/auto-research/identifiability/`
- HSE sensitivity: `reports/auto-research/hse-robustness/`
- Alias/exposure audit:
  `reports/auto-research/existing-data/alias-anchor-reanalysis/`

Raw JSONL and manifests are authority; generated reports are reproducible
views. The cost ledger/report use complete API-returned token usage and frozen
prices, not a provider billing invoice.

## Frozen hashes

- AR-001 config SHA256:
  `462aa3a7ccbdac52be1d34050eb9c497ee0da9a9eab03740996e0080b23e6d90`
- AR-001 probe SHA256:
  `7c5370122b553dafbd1ef950f3b4de9ca9636f7c3922cb31800169638b59c2df`
- AR-001 runner module SHA256:
  `b10f649b902f7f1a93fa9b576740f4a9c0465ed7059cabe0b9495421d6f369d8`
- Clean-v2 society probe hash:
  `cb234422389ff7d5a04566112a483f147e4a3d1212b1c69fbb0396ec9ca4c55e`

## Scientific cautions

- The 168 AR-001 rows are 56 exact prompts with three stochastic replicates,
  not 168 independent tasks or societies.
- All AR-001 probes have `x=0`.
- Calibration probe responses are nested within context seeds; society probes
  are nested within run seeds.
- Probe bootstraps assess item sensitivity, not seed-level uncertainty.
- Historical runs with older semantics must not be pooled with clean v2.

