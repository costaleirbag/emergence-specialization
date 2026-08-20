# Post-V1 measurement-aware analysis provenance

- Starting registered analysis commit: `ef58ccb`
- Final analysis/repair commit: `e81ab3e`
- Final provenance/documentation commit: `9f7c231`
- Final diagnostics/report commit: `77686cc`
- Analysis protocol: `docs/mechanisms/POST_V1_MEASUREMENT_AWARE_ANALYSIS_PLAN.md`
- Registry: `reports/post-v1-measurement-aware/analysis_registry.json`
- External model calls: `0`
- New inference cost: `US$0.00`
- Raw inputs: clean Theory V1.1 Stage A, MICRO, canonical MACRO events,
  canonical MACRO steps, and canonical MACRO checkpoint observations.
- Quarantined historical serial MACRO: excluded from every scientific table.
- Historical pre-measurement report: preserved and not overwritten.
- Primary output namespace: `reports/post-v1-measurement-aware/`
- Full validation: 290 unittest tests passed; `compileall` passed.

The analysis source and tests are added after the registration commit. Any
generated CSV/JSON/figure is a deterministic derivative of the five hashed raw
inputs. The final repair commits and input hashes are recorded above and are
verified before handoff.
