# Task ecology generators v1

## Shared design

OPE and CWDE are deterministic Python instruments. Each environment seed creates
run-specific latent theta after pretraining; theta is retained in host metadata,
never rendered. Training and evaluation cases use separate templates and entity
IDs, exact symbolic fields, and simulator-owned answers. Feedback-only memories
contain only a rendered resolved case and its correct output.

The four family IDs (`ACCESS`, `RELEASE`, `INCIDENT`, `PROVENANCE`) are host
metadata. They are not printed as niche labels in prompts.

## OPE — Organizational Procedure Ecology

OPE renders access, release, incident, and evidence/provenance cases with role,
resource, criticality, approval, lineage, time-window, and unusual-condition
features. The hidden rulebook has exactly three substantive parameters:

- ACCESS/RELEASE share threshold and role/resource compatibility parameters;
- INCIDENT/PROVENANCE share threshold and lineage-requirement parameters;
- each niche has one additional exception/temporal parameter.

Answers are exactly `APPROVE`, `DENY`, `ESCALATE`, or `DEFER`. Candidate theta
spaces have 12 states per family. The designed overlap is block-structured, not
implemented by answer balancing.

## CWDE — Causal Workflow Diagnosis Ecology

CWDE renders fictional incident logs with dependency markers, retries,
acknowledgements, validation gaps, and unusual conditions. ACCESS/RELEASE share
a chain motif; INCIDENT/PROVENANCE share a fan-out motif. Each niche receives a
run-specific permutation of four remediation classes and an exception policy.

Answers are exactly `ROLLBACK`, `RETRY`, `ISOLATE`, or `ESCALATE`. Candidate theta
spaces have 48 states per family. The topology is more diagonal because the
codebook is niche-specific while only the broad causal motif is shared.

## Deliberate limitations

These are synthetic procedural instruments, not realistic organizations or
production diagnostics. Their value is exact latent state, exact verifiers,
controlled transfer, and contamination resistance. They do not by themselves
establish ecological realism or specialization.

