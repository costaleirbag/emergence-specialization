# Relation-Signal Causal Transfer V1 — Execution Log

This file records the frozen learner-level intervention. It does not authorize
or contain a society experiment.

## Pre-inference freeze

- Protocol: `RELATION-SIGNAL-CAUSAL-TRANSFER-V1`
- Purpose: test whether fixed learner-visible relation cues change realized
  transfer geometry, using the completed V2 cross-domain observations as the
  no-signal reference.
- Provider/model: DeepSeek Direct / `deepseek-v4-flash`
- Thinking: off
- Natural history length: `h=8`
- Environment seeds: `9201, 9202, 9203, 9204`
- Geometries: `GLOBAL`, `BLOCK`, `DIAGONAL`
- Arms: `R0`, `RS`, `RI`
- Cross-domain underlying tasks: `1,152`
- New logical completions: `3,456`
- New external hard cap: US$0.15 including technical retries
- No OMP, no society, no routing, no follow-up inference

The R0/RS/RI sentence is inserted before the unchanged V2 semantic history and
target rendering. Geometry names, theta identifiers, canonical-factor IDs,
source actions, and correct target outputs are never added to the model-facing
prompt.

The manifest, prompt hashes, deterministic execution order, source-policy
identifiability table, and cost forecast must be frozen before the first paid
completion. Existing V2 cross-domain responses are reused as `R_NONE`; they are
not rerun.

## Qualification boundary

The primary experimental unit is the environment seed. The campaign can only
classify learner-level relation control as established if all preregistered
R1–R7 gates pass. Any society interpretation is explicitly out of scope and
requires separate principal-researcher review.

## Provenance

Starting HEAD and final execution commit are recorded in the immutable campaign
manifest and in the post-run report. This log is intentionally updated only at
freeze, execution, and analysis milestones; no scientific adaptation is allowed
between geometries or cue arms.
