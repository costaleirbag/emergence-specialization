# Emergent Specialization

This repository is a controlled pilot for a narrow question: can initially
homogeneous LLM agents develop persistent, useful task differentiation solely
from asymmetric feedback histories? The complete scientific design, controls,
and methodological cautions are in [Emergent Specialization.md](Emergent%20Specialization.md).

```mermaid
flowchart TD
  P["Python experiment controller"] --> E["Hidden-world environment"]
  P --> R["Confidence router"]
  P --> M["Explicit agent memories"]
  P --> Q["Fixed probes, metrics, JSONL logs"]
  P --> O["OMP JSONL/RPC adapter"]
  O --> A0["DeepSeek Flash copy 0"]
  O --> A1["DeepSeek Flash copy 1"]
  O --> AN["DeepSeek Flash copies 2–3"]
```

Codex is the development agent for this repository; it is not an experimental
agent. OMP is only an inference harness for copies of
`deepseek/deepseek-v4-flash`. Python owns identities, sampling, hidden rules,
routing, feedback, memory, checkpoints, random seeds, and all measurements.

## Setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

`uv sync` creates/updates the project environment and lockfile. No manual
`.venv` activation is needed; prefix project commands with `uv run`.

Install the optional notebook/report stack when you want visual analysis:

```bash
uv sync --group report
```

Check the installed OMP without printing credentials:

```bash
command -v omp
omp --version
omp --help
```

The requested model ID is declared in every real-run config. The harness never
silently substitutes another model.

## Run and test

Run the automated test suite (it never contacts DeepSeek):

```bash
uv run python -m unittest discover -s tests -v
```

Run the complete loop with the deterministic fake backend, without any model
calls:

```bash
uv run python -m emergent_specialization.experiment --config configs/pilot_private.yaml --dry-run
```

After confirming the local OMP runtime and model availability, run a 20-round
pilot under private feedback:

```bash
uv run python -m emergent_specialization.experiment --config configs/pilot_private.yaml
```

The shared-memory control is identical except for its feedback condition:

```bash
uv run python -m emergent_specialization.experiment --config configs/pilot_shared.yaml
```

The 20-round pilots make **400** DeepSeek calls each: 20 interaction rounds ×
4 agents (80), plus 40 fixed probes × 4 agents at checkpoints 0 and 20 (320).
They are intentionally not launched automatically.

Use `--num-rounds 10` and `--seed 2` for non-persistent overrides.

### DeepSeek through the local Bitwarden CLI

When DeepSeek credentials are supplied by the local Bitwarden CLI, run a real
experiment through the repository launcher rather than setting
`omp_executable` to a credential-fetching OMP wrapper. The experiment starts a
fresh OMP process for every completion, so a wrapper at that boundary would
query Bitwarden once per call.

```bash
scripts/run-deepseek-experiment.sh --config configs/smoke_real_private.yaml
```

The launcher obtains exactly one Bitwarden item named `DeepSeek API`, syncs the
vault, retrieves its Password, locks Bitwarden before starting Python, and then
passes only `DEEPSEEK_API_KEY` to the experiment process tree for that one
execution. It never writes a key to a file or passes `BW_SESSION` to Python or
OMP. The smoke config is intentionally two rounds with no checkpoints, so it
is an integration check rather than a scientific pilot.

## Experimental controls

- Four agents begin with an identical model ID, system prompt, decoding intent,
  empty memory, and tool access. Agent IDs live only in Python and are not
  inserted into model prompts.
- The four modular rules are environment-only. Prompts provide only an opaque
  world label, `x`, `y`, and answer choices.
- Every OMP completion starts a new process using `--mode rpc --no-session`.
  The adapter also passes `--no-tools --no-skills --no-rules --no-extensions
  --no-lsp --no-pty`. Thus OMP conversation history, compaction, tools, and
  project memory do not act as scientific memory.
- The only model-visible history is an explicit list of selected feedback
  experiences. The baseline uses `recent_k: 8`, giving every agent the same
  context budget. Probe evaluation receives frozen snapshots and cannot update
  memory.
- OMP 17.2.10 documents model and thinking controls in its CLI/RPC interface,
  but not temperature, top-p, or max-tokens controls. Those fields are logged
  as experimental intent and are not falsely claimed as enforced by OMP.
- A no-prompt local OMP smoke test did emit an `autoresearch` extension UI
  widget even with `--no-extensions`. It is not a model tool under
  `--no-tools`, but should be audited or disabled in the OMP installation
  before treating a real run as a completely feature-free baseline.

## Outputs

Each run creates `data/runs/<run-id>/` containing:

- `metadata.json`: config, hashes, runtime and backend metadata;
- `events.jsonl`: every inference attempt, parse failure/retry, round, and
  checkpoint event;
- `metrics.jsonl`: checkpoint behavioral matrices and derived metrics;
- `summary.json`: final routing, memory counts, metrics, and token/cost
  accounting when the provider exposes usage.

### Token usage and cost accounting

The OMP adapter records a provider usage payload when an RPC frame exposes one.
If OMP does not expose usage, the run summary explicitly reports
`status: unavailable`; the harness never estimates tokens from characters or
silently invents a monetary total. Monetary values are estimates based on rates
you provide in the YAML config, expressed per million tokens:

```yaml
cost:
  currency: USD
  input_per_million_tokens: null
  cached_input_per_million_tokens: null
  output_per_million_tokens: null
```

Set rates from the provider's current billing page for the exact model and
account before treating `summary.json`'s `estimated_cost` as meaningful. Raw
usage remains attached to each inference event, while the run-level `usage`
object reports coverage, totals, pricing, and an explicit status such as
`estimated`, `pricing_not_configured`, or `unavailable`.

Raw JSONL is the scientific record. It intentionally stores tasks, the exact
memory inserted into each prompt, prompt hashes, raw responses, parsed values,
latency, and errors—but never credentials. Derived checkpoint metrics include
individual/per-domain accuracy, utilization entropy, task-agent mutual
information, oracle gain, cosine behavioral distance, exact single-linkage HSE,
and normalized variants. Routing robustness remains a future extension.

## Executed notebook and visual report

The raw run remains the source of truth. Reports are derived, reproducible
artifacts generated from a completed run; notebook cells never perform model
inference or update agent memory.

Generate an executed notebook and standalone HTML report:

```bash
uv run --group report emergence-report --run data/runs/<run-id>
```

Or request the report at the end of an experiment:

```bash
uv run --group report python -m emergent_specialization.experiment \
  --config configs/pilot_private.yaml \
  --report
```

Compare private/shared conditions or several seeds:

```bash
uv run --group report emergence-compare --runs \
  data/runs/<private-run-id> \
  data/runs/<shared-run-id>
```

Each generated `reports/<report-id>/` contains:

- `report.ipynb`: executed, ordered Jupyter notebook;
- `report.html`: clean standalone report with code inputs hidden;
- `figures/`: SVG and PNG exports;
- `tables/`: CSV analysis tables;
- `report-manifest.json`: input/output hashes and package versions.

The single-run report covers metric trajectories, competence and routing
heatmaps, controlled-memory growth, round dynamics, confidence diagnostics,
probe success rasters, behavioral distance/dendrograms, and inference health.
The comparison report emphasizes permutation-invariant metrics so raw agent
labels are not averaged across seeds without alignment.
