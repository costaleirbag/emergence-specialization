# Observable Learner Calibration V2 — report

## Executive result

**Status: PARTIAL learner geometry; no society experiment authorized.**

The harness-corrected DeepSeek Direct run completed **1,920/1,920 logical
completions**, with 1,920 physical attempts, zero retries, zero semantic OOD
responses, full usage coverage, and observed cost **US$0.0406882448**. All
responses came from `deepseek-v4-flash` with one provider fingerprint. The
learner shows positive diagonal gains in all three geometries, but it does not
realize the preregistered GLOBAL/BLOCK/DIAGONAL transfer geometry: GLOBAL
off-diagonal transfer is negative on average, BLOCK within-block transfer is
zero and its block contrast is negative, and the required `Q` ordering fails.

This is a result about the learner-response arrow `J_obs, L*_obs -> L^DS` only.
It is not evidence for or against society-level specialization.

## What was known before inference

V3.1 passed its ten offline observation-channel gates, including zero observation
loss, zero renderer collisions, zero theta leakage, 100% family recovery, and
reproducible `J_obs`/`L*_obs`. V1 is superseded as a clean calibration: its
static instruction contained `[0,1,0]` and its probes had unbalanced symbolic
support. See [the V1 harness audit](LEARNER_CALIBRATION_V1_HARNESS_AUDIT.md).

V2 removed those defects without changing the ecology, histories, model, or
semantic renderer.

## Frozen protocol and technical health

| item | value |
|---|---:|
| provider/model | DeepSeek Direct / `deepseek-v4-flash` |
| thinking | off |
| seeds | 9201, 9202, 9203, 9204 |
| geometries | GLOBAL, BLOCK, DIAGONAL |
| natural memory | h=8, teacher-correct, feedback-only |
| probes | 8 per seed × target; eval template only |
| logical completions | 384 baseline + 1,536 transfer = **1,920** |
| physical attempts | 1,920 |
| retries / semantic OOD | 0 / 0 |
| logical coverage / usage coverage | 100% / 100% |
| mean / median latency | 1.223 s / 1.187 s |
| input / cached input / output tokens | 1,048,704 / 815,616 / 20,615 |
| observed cost | **US$0.0406882448** |

The model identity and fingerprint were constant. The run status bookkeeping
was corrected after completion so `physical_attempts=1920`; the append-only raw
journal was correct throughout and was not rerun.

The frozen probe audit has exactly two occurrences of each input value 0–3 in
each coordinate, eight unique probes per seed, and zero history overlap. The
exact Bayes precondition passed: informative mean `A* = 0.984375` in each
geometry and independent cells exactly `A* = 0.125`.

## Baseline competence

Empty-memory exact three-bit accuracy was 0.2188 (GLOBAL), 0.1406 (BLOCK), and
0.1641 (DIAGONAL). The aggregate baseline accuracy across geometries was 0.1771.
Family baselines (pooled over geometries) were ACCESS 0.2292, INCIDENT 0.1562,
PROVENANCE 0.1667, and RELEASE 0.1458. These differences are descriptive and
make small transfer gains noisy; they are not role evidence.

## Realized transfer matrices

Rows are source-history families and columns are target families; entries are
`L^DS` accuracy gain relative to the same probe with empty memory. The exact
Bayes opportunity is shown in the corresponding `L*_obs` CSV.

### GLOBAL

```text
             ACCESS  INCIDENT  PROVENANCE  RELEASE
ACCESS        0.156   -0.125      0.000    -0.031
INCIDENT     -0.156    0.188      0.094    -0.031
PROVENANCE   -0.094   -0.062      0.312    -0.031
RELEASE      -0.062   -0.094      0.000     0.375
```

`D=0.2578`, `O=-0.0495`, `Q=0.3073`, `O/D=-0.1919`. GLOBAL therefore does not
show the expected dense positive cross-niche transfer despite `L*_obs` being
dense.

### BLOCK

```text
             ACCESS  INCIDENT  PROVENANCE  RELEASE
ACCESS        0.125    0.094      0.125     0.094
INCIDENT      0.062    0.312     -0.031    -0.062
PROVENANCE   -0.125    0.000      0.281     0.000
RELEASE      -0.062    0.031      0.000     0.156
```

`D=0.2188`, `O=0.0104`, `Q=0.2083`, `W=0.0000`, `C=0.0156`, `B=-0.0156`.
The intended within-block advantage is absent in this pilot.

### DIAGONAL

```text
             ACCESS  INCIDENT  PROVENANCE  RELEASE
ACCESS        0.125    0.000      0.000     0.000
INCIDENT     -0.031    0.125     -0.031     0.000
PROVENANCE   -0.156   -0.062      0.219     0.094
RELEASE      -0.094   -0.062     -0.062     0.281
```

`D=0.1875`, `O=-0.0339`, `Q=0.2214`, `O/D=-0.1806`. This is the only geometry
whose qualitative result is consistent with locality: positive same-niche gain
and little positive off-diagonal gain.

Seed-level `Q` values were GLOBAL `(0.3333, 0.3438, 0.3333, 0.2188)`, BLOCK
`(0.2812, 0.1875, 0.2604, 0.1042)`, and DIAGONAL `(0.0833, 0.2812, 0.3021,
0.2188)` for seeds 9201–9204. The geometry ordering is **FAIL**.

## Geometry alignment and learner-induced transfer

Raw/cellwise alignment with exact `L*_obs` was GLOBAL 0.1753, BLOCK 0.5912, and
DIAGONAL 0.8031. Centered cosine was unavailable for GLOBAL because its exact
matrix is constant; BLOCK was 0.4501 and DIAGONAL 0.9322. Spearman values were
0.8065, 0.8678, and 0.9486 respectively, but these are descriptive with only
16 cells per geometry.

The zero-information controls show that realized transfer need not be ecological
transfer. Mean zero-`J` gain was **+0.0156** in BLOCK cross-block cells (4/8
aggregate cells positive) and **−0.0339** in DIAGONAL off-diagonal cells (1/12
positive). These values can contain generic context practice, semantic priors,
anchoring, interference, and baseline noise.

## Components and response distribution

Component-level `(D,O,Q)` values were:

| geometry | component 1 | component 2 | component 3 |
|---|---:|---:|---:|
| GLOBAL | (0.031, 0.010, 0.021) | (0.281, 0.115, 0.167) | (0.219, 0.010, 0.208) |
| BLOCK | (0.063, −0.052, 0.115) | (0.313, 0.229, 0.083) | (0.313, 0.094, 0.219) |
| DIAGONAL | (0.156, 0.031, 0.125) | (0.281, 0.094, 0.188) | (0.125, −0.177, 0.302) |

Joint exact correctness remains the primary outcome. Components are a secondary
diagnostic and are not selected post hoc.

Baseline output entropy was 2.306 bits and its modal output `[1,1,1]` occurred
in 49.0% of responses. Transfer entropy rose to 2.947 bits and the modal
fraction fell to 17.5%; same-niche and cross-niche transfer were 2.979 and 2.929
bits. Thus the V1 fixed-vector collapse is not reproduced by this neutral
schema, although answer priors remain visible (baseline bit-one rates were
0.766/0.680/0.708).

## Anchoring and family effects

Across geometries, any-memory joint-action copying occurred in about 84–85% of
transfer responses, while exact last-action copying was 19.5–23.6%. Responses
that matched any memory action were less accurate than non-matching responses:
GLOBAL 0.223 vs 0.366, BLOCK 0.186 vs 0.293, and DIAGONAL 0.177 vs 0.234.
This is a descriptive confound, not a causal estimate of copying.

Pooled target gains were ACCESS −0.026, INCIDENT +0.029, PROVENANCE +0.076, and
RELEASE +0.070. The learner therefore had family-asymmetric behavior, but this
does not establish acquired semantic roles.

## Qualification gates

| gate | result |
|---|---|
| local `D >= 0.10` in all geometries | PASS |
| GLOBAL dense transfer `O/D >= 0.50` | FAIL |
| BLOCK `W>0`, `B>=0.05` | FAIL |
| DIAGONAL locality `O/D <= 0.50` | PASS |
| `Q_GLOBAL < Q_BLOCK < Q_DIAGONAL` | FAIL |
| positive alignment with exact `L*_obs` | PASS |

Overall: **PARTIAL**, not qualified. This is a conservative engineering gate,
not a statistical significance claim. The result says that DeepSeek can exhibit
small same-niche gains under the corrected interface, but the current four-family
ecology does not yet yield a clean realized transfer geometry suitable for a
society test.

## What this does not establish

- no society, routing, private/shared memory, or specialization was tested;
- no causal claim that memory creates roles;
- no claim that a failed geometry gate disproves in-context learning;
- no general foundation-model conclusion from four environment seeds;
- no conclusion that semantic families are intrinsically difficult or easy;
- no claim that `T(L^DS)` is an LLM-society Jacobian.

The correct hierarchy remains: `G` designed, `J_obs` offline, `L*_obs` Bayes
opportunity, `L^DeepSeek` measured here, `T(L^DeepSeek)` derived only under an
explicit effective model, social organization not measured.

## Exact next scientific question

Principal-researcher review should decide whether the partial result is a useful
negative/diagnostic ecology control or whether a separately preregistered
single-agent mechanistic diagnostic is warranted. Do not run a society, add
seeds, change prompts, enable thinking, or tune the ecology automatically.
