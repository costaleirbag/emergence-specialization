# Clean v2 2×2 mechanism report

**Status: descriptive aggregate only.** This report records the completed clean
response-semantics campaign. It does not claim a causal effect, confirm
specialization, or select a preferred condition.

## Protocol and provenance

- Campaign: `developmental-dynamics-v2`
- Protocol identity: `staged-v3-response-semantics`
- Cells: confidence/private, confidence/shared, random/private, random/shared
- Seeds: 1–10 in each cell (40 runs)
- Four agents, 20 interaction rounds, checkpoints `[0, 10, 20]`, 40 probes per checkpoint
- DeepSeek Direct, `deepseek-v4-flash`, thinking disabled, Python-controlled `recent_k=8` memory
- Fixed probe-set hash: `cb234422389ff7d5a04566112a483f147e4a3d1212b1c69ec9ca4c55e`
- No legacy v1 artifacts were used in the v2 aggregate.

The first 35 runs were recorded under the campaign tooling commit
`d49cc07b9bb81a966d6072e34bfe957e4befb6a7`; the final resumed run and the last
three runs were recorded after the infrastructure-only checkpoint-resume fixes,
ending at `2f9f2138bc78b0a9d1cdfd6f7fee817f996de77c`. The fixes do not change task
generation, prompts, routing, memory, probes, or scoring; they only prevent
repeating completed work and use the immutable memory snapshot when an older
checkpoint must be completed after later rounds are present.

## Health and cost

| Quantity | Value |
|---|---:|
| Runs | 40 / 40 |
| Logical completions | 22,400 / 22,400 |
| Physical attempts | 22,436 |
| Recovered attempts | 34 |
| Empty provider content | 26 |
| Timeout/transient transport | 4 |
| Technical parse errors | 6 |
| Rate limits / server errors | 0 / 0 |
| Valid scientific out-of-domain answers | 25 |
| Observed cost | USD 0.649597 |

Health classification is `HEALTHY / CLEAN` for 18 runs and `HEALTHY / RECOVERED`
for 22 runs. Every run has complete logical coverage. Recovered runs remain
included but are flagged; retries and missing usage are not hidden.

An answer such as `{"answer": 7, "confidence": 0.2}` is now a completed model
response with `answer_in_domain=false`, not a technical parse error or retry.
Its correctness is false, and its original answer remains in interaction memory
if selected. This is a scientific model output and is reported separately from
transport, malformed-output, and retry failures.

## Endpoint table (means across the ten seeds)

| Cell | normalized HSE(20) | Phi(20) | normalized MI(20) | utilization(20) | oracle gain(20) | routing eta(20) |
|---|---:|---:|---:|---:|---:|---:|
| confidence/private | 0.5548 | 0.0100 | 0.2637 | 0.8668 | 0.2275 | -0.0181 |
| confidence/shared | 0.2873 | 0.0047 | 0.2694 | 0.9631 | 0.1000 | 0.0537 |
| random/private | 0.4704 | 0.0080 | 0.1915 | 0.9256 | 0.1700 | 0.0172 |
| random/shared | 0.2135 | 0.0043 | 0.1915 | 0.9256 | 0.0550 | 0.1149 |

These are endpoint summaries, not evidence that any cell is “better”. HSE is
behavioral diversity, Phi is competence differentiation, MI is organization of
routing by world, utilization is concentration/dispersion, and oracle gain is
complementarity potential. None alone defines useful specialization.

## What the 2×2 makes measurable

The confidence/random contrast is an analysis control for confidence-driven
selection. The private/shared contrast is the information-locality manipulation.
Together they permit a later factorial analysis of descriptive trajectories,
including HSE, Phi, utilization, MI against a permutation null, routing
alignment, matching gain, online accuracy, and out-of-domain-answer rates.

The current report intentionally stops before inferential statistics. A future
analysis must preserve seed pairing, account for recovered attempts, include
provider fingerprints, and distinguish agent-label-invariant summaries from raw
label counts.

## Reproducible artifacts

The machine-readable report is in
`reports/campaigns/developmental-dynamics-v2/clean-2x2/`:

- `run_inventory.csv` — selected manifest run and health row;
- `checkpoint_metrics.csv` — one row per run/checkpoint;
- `tidy_metrics.csv` — long-format metric table;
- `competence_long.csv`, `routing_long.csv` — heatmap-ready matrices;
- `online_rounds.csv`, `online_observables.csv` — interaction-only trajectories;
- `clean_2x2_summary.json` — aggregate provenance and health summary;
- `figures/` — SVG trajectories and endpoint competence/routing heatmaps.

Regenerate offline with:

```bash
UV_CACHE_DIR=/tmp/uv-cache-es uv run python -m emergent_specialization.clean2x2_report
```

No provider, credential, or network access is needed for this command.

## Guardrails for interpretation

1. Diversity is not specialization.
2. Competence differentiation is not useful division of labor.
3. High routing concentration can be collapse.
4. MI describes organization, not competence.
5. Oracle gain and matching gain describe potential complementarity.
6. The private/shared contrast is the intended causal manipulation, but these
   40 runs alone are not a causal conclusion.
7. The old v1 runs remain `LEGACY / EXPLORATORY` and must not be mixed into this
   clean v2 dataset.

## Response anchoring and synchronization audit

An offline audit found higher pairwise answer agreement at t=20 in shared-memory
probes: confidence/shared 0.654 versus confidence/private 0.334, and
random/shared 0.708 versus random/private 0.438. Shared cells also copied labels
from common memory frequently. This is compatible with a
memory-to-anchoring-to-synchronization pathway, but is not proof of mechanism or
useful competence. Full tables are in `reports/response-anchoring/` and the
definitions/caveats are in `docs/RESPONSE_ANCHORING_AUDIT.md`.
