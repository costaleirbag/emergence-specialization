# Semantic task ecology qualification — final report

## Scope

This was a single-agent qualification of learning-transfer geometry. It was not
a society experiment and does not establish role formation, specialization, or
division of labor.

## Provenance

- branch: `research/developmental-dynamics`
- final HEAD: `15931de20908b09f03e1b37e321161ebdf730b5f`
- model: DeepSeek Direct `deepseek-v4-flash`
- thinking: off
- predeclared environment seeds: `1701..1705`
- replicates: 2
- probes per target niche: 8, balanced 2/class
- protocol: `ECOLOGY-TRANSFER-QUALIFICATION-V1`
- AR-001B probe hash: `ac0a8df29f25f1ed5f85f5e48b8ece8cf3947203fd1d27b479b2cd071adb2936`
- OPE tasks hash: `c4309b111a27fc5ee1f9f6a570d12db68f7b47fdb51a88baefdb7ea29ea47dc3`
- CWDE tasks hash: `2f8b39e52f81bded2cf779d3d284de6ed85ec8ac981e9135aa5a8cacf5ef5860`

## Results

| candidate | logical | physical | technical retries | semantic OOD | cost USD | baseline | D | O | Q | classification |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| OPE | 1920 | 1920 | 0 | 1 | 0.04292984 | 0.41875 | 0.13125 | 0.03229 | 0.09896 | PROMISING SPECIALIZATION SUBSTRATE |
| CWDE | 1920 | 1920 | 0 | 4 | 0.03843200 | 0.22500 | 0.13438 | 0.04271 | 0.09167 | PROMISING SPECIALIZATION SUBSTRATE |

OPE `B_OPE = 0.01250`. OPE niche contrasts are
`ACCESS=0.2125`, `INCIDENT=0.0500`, `PROVENANCE=0.0792`, and `RELEASE=0.0542`.
CWDE contrasts are `ACCESS=0.0917`, `INCIDENT=0.2167`, `PROVENANCE=0.1125`,
and `RELEASE=-0.0542`.

Both classifications are preregistered descriptive gates. They mean that the
single-agent ecology exhibited positive diagonal learning and comparative
advantage under this qualification; they do not license a society run or a
claim of emergent specialization.

## Health and cost

AR-001B used 112/112 physical calls, no technical retries, and cost
US$0.00196084; exact 2-D arithmetic accuracy was 0.3393, below the frozen
0.70 substrate threshold. OPE and CWDE used the same expected model and one
provider fingerprint. The campaign total was US$0.08332268 against the hard
US$0.50 cap, with zero reserved balance at completion.

All semantic OOD responses were retained as incorrect completed observations;
none was retried. OPE initially stopped on its first OOD response, then resumed
append-only after the plumbing fix without repeating existing logical IDs.

## Explicit non-goals completed

- society experiments: 0
- Gate 2: not run
- new models: 0
- follow-up tuning: 0
- additional seeds: 0

See the candidate-specific CSV/JSON/SVG artifacts under
`reports/task-ecology/qualification-v1/ope/` and `.../cwde/`, plus the raw
JSONL events under `data/auto-research/ecology-transfer-qualification-v1/`.
