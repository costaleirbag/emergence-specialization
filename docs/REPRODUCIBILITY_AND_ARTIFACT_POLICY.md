# Reproducibility and artifact policy

## Source of truth

Scientific claims require a versioned protocol/configuration, the Git commit
that produced it, immutable raw events, a machine-readable health record, and a
report that states the experimental unit and all exclusions. Derived figures
must be reproducible from raw artifacts; hand-edited numbers are not evidence.

The root `Emergent LLM Societies.md` is the living narrative context. Focused
reports in `docs/` are the authoritative record for individual phases. A report
marked `SUPERSEDED` remains historical and must not be used as the current
conclusion.

## Tracked versus local artifacts

- Source, tests, configs, protocols, reports, manifests, and provenance notes
  belong in Git when they are small enough to review.
- Raw paid run journals, generated figures, local campaign ledgers, caches, and
  machine-local calibration data stay local unless a protocol explicitly says
  otherwise. Existing raw data are never deleted during maintenance.
- Handoff packages and sidecar checksums live under `.artifacts/packages/`.
  The directory is intentionally ignored so large bundles do not silently enter
  source history. Their names, sizes, SHA-256 values, status, and canonical
  reports are indexed in [ARTIFACT_INDEX.md](ARTIFACT_INDEX.md).
- Secrets, Keychain material, Bitwarden state, `.env` files, and credentials
  never belong in the repository or an artifact package.

## Minimum provenance for a new run

Record the Git HEAD, config and probe hashes, model/provider identity, decoding
configuration, seed(s), task-sequence semantics, retry policy, timestamps,
usage/cost fields, and a health classification. Preserve append-only events and
distinguish logical completions from physical attempts. A recovered run may be
included only with its recovery flag visible; an incomplete run is not silently
included in aggregate claims.

## Analysis repair

Repairs must read immutable raw events, write to a separate derived location,
record before/after hashes, state whether new model calls were made (normally
zero), and retain the superseded output. A bookkeeping correction must not alter
raw observations or silently change a preregistered threshold.

## Reproduction checklist

1. Check out the recorded commit and verify the config/probe hashes.
2. Run the documented offline tests and compile check.
3. Validate provider/model identity and credentials without printing secrets.
4. Run health accounting before interpreting scientific metrics.
5. Generate derived tables/figures from the preserved raw artifacts.
6. Archive the exact report, manifest, and checksum used for handoff.
