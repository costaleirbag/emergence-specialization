# OPE Information Geometry V3.1 observation specification

Status: frozen offline observation instrument; no LLM call is authorized by
this document.

V3.1 preserves the V3 latent prior: four canonical families, 64 symbolic cases
per family, three binary outputs, six balanced Boolean maps, and unchanged
GLOBAL/BLOCK/DIAGONAL sharing. It changes only the learner-facing observation
map and the estimators.

## Structured observation O

Each case becomes a structured object with:

- `domain_semantics`: a short operational description;
- `context`: one domain-identifying sentence;
- `attributes`: three ordered `{name, value}` pairs;
- `decision_semantics`: three domain-appropriate decision descriptions.

`O` contains no host family ID, geometry, seed, theta index, canonical factor
number, or hidden map. `C_hat(O)` is a deterministic host-side decoder from the
domain semantics. It is an audit function, not a learned classifier.

## Family schemas

### ACCESS

Context: a person or service requests access to an organizational resource.

1. Resource sensitivity: routine internal material; sensitive operational
   material; confidential records; critical restricted records.
2. Requester authorization: unverified requester; identity-verified requester;
   authorized team member; resource owner.
3. Request timing: ordinary request; scheduled exception; urgent operational
   need; emergency exception.

Outputs are semantically phrased as permit the request, escalate for review,
and release access immediately; internally they remain the same three bits.

### INCIDENT

Context: an operational incident affects a live service.

1. Incident impact: localized interruption; degraded service; major service
   disruption; critical outage.
2. Response readiness: unverified response; initially triaged; contained
   response; fully prepared response.
3. Incident timing: stable period; active investigation; urgent response
   window; emergency escalation.

Outputs are authorize the response, escalate the incident, and act immediately;
the host mapping remains bitwise unchanged.

### PROVENANCE

Context: an artifact or report is reviewed for evidence lineage.

1. Evidence importance: routine record; material record; sensitive evidence;
   critical evidence.
2. Lineage completeness: missing lineage; partial lineage; verified lineage;
   audited lineage.
3. Evidence timing: historical context; recent update; current record;
   exceptional deadline.

Outputs are accept the evidence, escalate for review, and use it immediately.

### RELEASE

Context: a software or service change is reviewed for deployment.

1. Release criticality: routine change; important change; high-impact change;
   mission-critical change.
2. Release readiness: draft change; reviewed change; approved change; validated
   change.
3. Release timing: planned window; expedited window; restricted change window;
   exception window.

Outputs are approve the release, escalate for review, and deploy immediately.

## Canonical replay and templates

The host maps the four semantic values in each position back to `x_j=0,1,2,3`
exactly. The future model does not receive this replay map. Four deterministic
templates exist for each family. Template IDs 0,1,2 are training-only and ID 3
is evaluation-only. Template changes affect wording/order only, never O or Y.

The renderer audit exhaustively checks all 4 families × 64 states × 4
templates. Cross-family text collisions and hidden-policy leakage must be zero.

The blind renderer is a diagnostic only: it replaces domain context with a
generic case and values with `level_0`...`level_3`. It is not a future LLM
benchmark.
