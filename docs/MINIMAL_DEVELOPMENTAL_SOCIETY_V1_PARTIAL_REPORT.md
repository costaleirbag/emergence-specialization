# Minimal Developmental Society V1 — partial execution brief

> **Snapshot:** 2026-08-11T14:50:54Z  
> **Status:** execution still in progress; this is a technical handoff, not a
> scientific result report.

## Purpose

This brief is intended for the central research orchestrator. It summarizes the
frozen protocol and the current execution state without interpreting partial
trajectories. The campaign must finish before `Psi_spec`, `Phi`, matching gain,
routing organization, team utility, role persistence, or emergent-specialization
claims are analyzed.

## Frozen experiment

- Protocol: `MINIMAL-DEVELOPMENTAL-SOCIETY-V1`
- Manifest hash: `7a08e7a032c9e09b3bb32c294c2be065c0002dc857ce771aae46efcb0a8d868a`
- Provider/model: DeepSeek Direct / `deepseek-v4-flash`
- Thinking: off
- Geometry: V3.1 `DIAGONAL`
- Seeds: `27101`–`27108`
- Regimes: `RP`, `AP4`, `AP12`, `AS12`
- Agents: 4; rounds: 128; checkpoints: `[0,16,32,64,96,128]`
- Controlled memory: host-side `recent_k=8`
- Expected logical completions: `47,104`
- Hard campaign cap: `US$2.25`

## Technical snapshot

At this snapshot, the append-only event log contains approximately 29.5k
physical completion attempts and 29.5k terminal logical observations; the exact
current values should always be read from `run_status.json` and recomputed from
`events.jsonl`, because the run is still advancing.

The campaign originally stopped after 29,188 terminal logical completions when a
provider response omitted usage/cost data. The response was not admitted as a
scientific observation. The recovery added one retroactive nonterminal technical
event with a conservative `US$0.0005` charge, preserving the same logical ID for
attempt 1. A later transient transport failure was also recorded as a technical
attempt. Both categories are retryable infrastructure events, not scientific
conditions.

The current ledger and event costs are reconciled; the hard cap remains active.
Recorded terminal model identity remains `deepseek-v4-flash`. Semantic
`out_of_domain` responses are retained as scientific observations and are never
retried.

## Interpretation boundary

Do **not** infer specialization, learning, regime differences, or causal effects
from the partial event stream. Partial checkpoint coverage is selected by the
frozen execution schedule and is not a planned stopping point. Do not adapt
seeds, regimes, routing, prompts, memory, or budget based on intermediate
outputs.

## Authoritative artifacts

- Frozen design: `reports/society/minimal-developmental-society-v1/manifest.json`
- Live status: `data/auto-research/minimal-developmental-society-v1/run_status.json`
- Append-only events: `data/auto-research/minimal-developmental-society-v1/events.jsonl`
- Cost ledger: `data/auto-research/minimal-developmental-society-v1/campaign_budget.json`
- Recovery provenance: `docs/MINIMAL_DEVELOPMENTAL_SOCIETY_V1_EXECUTION_LOG.md`
- Preregistration: `docs/MINIMAL_DEVELOPMENTAL_SOCIETY_V1_PREREGISTRATION.md`

The authoritative post-run analysis command is intentionally deferred until
terminal logical coverage reaches `47,104`.

## Handoff instruction

Continue the frozen campaign. After completion, validate logical coverage,
physical attempts, retry categories, model identity, cost, checkpoint
immutability, and artifact completeness first. Only then generate the full
offline report and interpret preregistered contrasts. If another usage/cost
failure occurs, treat it as infrastructure uncertainty and stop safely; do not
silently rerun a logical unit.
