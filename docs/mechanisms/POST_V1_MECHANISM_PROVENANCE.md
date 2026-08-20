# Post-V1 mechanism decomposition provenance

- Protocol: `POST-V1-MECHANISM-DECOMPOSITION`
- Analysis plan/registry frozen before derived results: commit `c74294f`
  (`Register post-V1 mechanism decomposition plan`).
- Primary inputs: clean Theory V1.1 Stage A, MICRO, and canonical MACRO only.
- Historical harness-confounded Theory V1 data: excluded from primary analysis.
- External model calls: `0`.
- New inference cost: `US$0.00`.
- Canonical MACRO terminal observations: `62,976`; physical attempts: `62,995`.
- State panel: `198,144` rows (`96 trajectories × 129 times × 4 agents × 4
  niches`).
- Raw hashes before/after analysis: identical; see
  `reports/post-v1-mechanisms/raw_hash_manifest.json`.
- Quarantined data: no primary use; `data/quarantine/` was preserved untouched.
- Theory status: Theory V1 closed; Theory V2 not defined.

The analysis is deterministic and read-only with respect to scientific raws.
Wall-clock timestamps and figure metadata are the only intentionally
non-scientific fields that may differ between repeated executions.
