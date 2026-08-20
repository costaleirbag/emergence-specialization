# Repository consolidation — August 2026

## Scope and safety

This maintenance pass consolidated provenance and Git hygiene only. It made no
external model calls, did not unlock credentials, did not alter raw run
directories, and did not start or resume an experiment. The working branch was
`research/developmental-dynamics` at start, with HEAD
`c97ba2fb808672078540181e7bbb7a76048e6bc6`.

## Scientific state preserved

The existing corrected conclusion remains unchanged: local plasticity is
qualified; social amplification is supported; functional organization is
partial; realized team utility did not pass its preregistered gate; emergent
functional specialization is not yet supported. The initial society analysis
remains available with a `SUPERSEDED` notice.

## Bookkeeping residues repaired

1. `corrected_verdict.json` now uses `functional_organization: PARTIAL` as the
   canonical scalar, matching `three_layer_verdict`. The old scalar
   `NOT SUPPORTED` is retained under `legacy_fields`.
2. The `last32_team_utility` row in `bug_impact_table.csv` now aggregates only
   rows with `segment == last32`. The raw online events and H6 calculation were
   not changed.

The repair source and tests include regression coverage for both properties.

## Artifact consolidation

Sixteen root-level `.tar.gz` bundles and ten checksum sidecars were moved to
`.artifacts/packages/`. Their bytes and SHA-256 values were verified after the
move and are indexed in [ARTIFACT_INDEX.md](ARTIFACT_INDEX.md). No archive was
deleted; no raw artifact was rewritten.

## Versioned documentation and source

Added/updated documentation includes the navigation map, experiment registry,
failure/bug registry, reproducibility policy, artifact index, and this report.
The public README now states the current scientific status. The root living
research context `Emergent LLM Societies.md`, project `AGENTS.md`, and historical
presentation working note were preserved as reviewable files.

## GitHub hygiene

Remote configured: `origin` points to the project GitHub repository. Local
inspection found `origin/main`, but the GitHub API and `git ls-remote` were not
reachable in this session and `gh auth status` reported an invalid token. No
issues, labels, PRs, or pushes were created. The following high-value issue
drafts should be created by a maintainer after authentication is restored:

- reproducible raw-artifact release/index policy;
- repair and provenance checks for derived society metrics;
- local-plasticity-to-society gate and follow-up design;
- provider/runtime health and cost observability;
- task-ecology construct-validity roadmap.

No direct push or merge was attempted. A future PR should target the repository's
default branch only after the maintainer confirms branch ancestry and reviews
these local commits.

## Validation

The final maintenance gate passed:

- `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -q` — **242
  tests, OK** (215.684 seconds).
- `PYTHONPATH=src .venv/bin/python -m compileall -q src` — **exit 0**.
- All ten retained checksum sidecars matched their moved archives.
- The repository root contains no remaining archive or checksum files.

The final local HEAD is recorded by the consolidation commit; repeat the same
commands in CI once GitHub access is restored.

## Intentional non-actions

- no DeepSeek/OMP/direct inference;
- no credentials or secrets accessed;
- no raw-data deletion or rewrite;
- no experiment rerun, resume, or scientific parameter change;
- no push, merge, rebase, or PR;
- no attempt to make a partial scientific result look conclusive.
