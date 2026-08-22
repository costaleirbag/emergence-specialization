# Code layout

The package is organized so that the directory tree states the project's own
chain of evidence. Infrastructure and science are deliberately separated: the
harness evolves, a completed study does not.

```text
src/emergent_specialization/
├── core/        invariant experimental substrate
├── providers/   model access and credentials
├── runtime/     execution and operations
├── metrics/     measurement instruments (the claim ladder)
├── studies/     frozen research phases, one subpackage per track
│   ├── ecology/       does the environment carry learnable structure?
│   ├── calibration/   does one agent realize it from experience?
│   ├── society/       does feedback locality organize a population?
│   ├── theory/        do frozen equations predict the dynamics?
│   └── mechanisms/    which arrow in the loop failed to close?
├── audits/      read-only forensic passes over completed data
└── reporting/   derived, reproducible artifacts
```

## Why these boundaries

**`core/`** holds what every phase shares and no phase may quietly change:
hidden worlds, agents, bounded memory, routing, the frozen probe set with its
hash check, the strict answer/confidence parser, exact GF(7) arithmetic. A
change here invalidates comparisons across phases.

**`metrics/`** is the claim ladder in code. HSE, mutual information,
utilization entropy, complementarity, and competence differentiation are
separate modules because they are separate constructs — behavioral diversity is
not competence, and neither is useful division of labor.

**`studies/`** follows the evidence chain, not the calendar. Each subpackage
answers one question, and the order is a dependency order: an ecology must show
learnable structure before a single agent is calibrated on it, and a learner
gate must qualify before a society runs. A completed study is provenance; its
numbers are cited by reports that name a commit.

**`audits/`** is separate from `reporting/` on purpose. An audit exists to
falsify a completed result and must never mutate a raw artifact; a report
renders one. Keeping them apart makes an audit's read-only contract structural
rather than a convention.

## Import convention

Intra-package imports are absolute (`from emergent_specialization.core.models
import Task`). At this nesting depth relative imports obscure which layer a
module depends on, and a study's imports should show at a glance that it draws
on `core`, `metrics`, and `providers` rather than on another study.

## Repository-root resolution

Modules that write into `reports/` or `data/` resolve the repository root from
their own depth:

```python
ROOT = Path(__file__).resolve().parents[N]   # N = 2 + depth below the package
```

`core/` and other single-level packages use `parents[3]`; two-level packages
such as `studies/society/` use `parents[4]`. Moving a module means updating `N`.

## Historical commands in frozen documents

Documents under `docs/` record commands against the module paths that existed
when they were written. Per the reproducibility policy, historical reproduction
checks out the recorded commit, where those paths are correct. To translate a
command to the current tree, use the map below.

## Old path to new path

| before | after |
|---|---|
| `agents` | `core.agents` |
| `aggregate` | `reporting.aggregate` |
| `alias_anchor_reanalysis` | `audits.alias_anchor` |
| `analysis` | `reporting.analysis` |
| `ar001b` | `studies.calibration.ar001b` |
| `batch` | `runtime.batch` |
| `benchmark.deepseek` | `runtime.benchmark.deepseek` |
| `campaign` | `runtime.campaign` |
| `clean2x2_report` | `reporting.clean2x2` |
| `clean_campaign` | `runtime.clean_campaign` |
| `config` | `core.config` |
| `costs` | `core.costs` |
| `credentials` | `providers.credentials` |
| `cross_domain_transfer_bottleneck` | `studies.calibration.cross_domain_bottleneck` |
| `deepseek_doctor` | `runtime.doctor` |
| `ecological_information` | `studies.ecology.ecological_information` |
| `ecological_information_v31` | `studies.ecology.ecological_information_v31` |
| `ecology_regime_observability` | `studies.ecology.regime_observability` |
| `ecology_transfer` | `studies.ecology.ecology_transfer` |
| `environment` | `core.environment` |
| `experiment` | `runtime.experiment` |
| `explicit_rule_execution` | `studies.calibration.explicit_rule_execution` |
| `gate1_report` | `reporting.gate1` |
| `gf7` | `core.gf7` |
| `health` | `runtime.health` |
| `hidden_rule_identifiability` | `audits.hidden_rule_identifiability` |
| `hse_robustness` | `audits.hse_robustness` |
| `interventions` | `core.interventions` |
| `journal` | `core.journal` |
| `local_plasticity_curve` | `studies.calibration.local_plasticity_curve` |
| `logging` | `core.logging` |
| `memory` | `core.memory` |
| `memory_learnability` | `studies.calibration.memory_learnability` |
| `memory_learnability_report` | `reporting.memory_learnability` |
| `memory_representation_thinking` | `studies.calibration.memory_representation_thinking` |
| `memory_representation_thinking_report` | `reporting.memory_representation_thinking` |
| `minimal_developmental_society` | `studies.society.minimal_developmental_society` |
| `minimal_developmental_society_analysis_repair` | `studies.society.analysis_repair` |
| `minimal_model.simulation` | `studies.society.minimal_model.simulation` |
| `models` | `core.models` |
| `observable_learner_calibration` | `studies.calibration.observable_learner_v1` |
| `observable_learner_calibration_v2` | `studies.calibration.observable_learner_v2` |
| `overnight_offline` | `audits.overnight_offline` |
| `parsing` | `core.parsing` |
| `post_v1_measurement.analysis` | `studies.mechanisms.measurement.analysis` |
| `post_v1_measurement.cli` | `studies.mechanisms.measurement.cli` |
| `post_v1_mechanisms.analysis` | `studies.mechanisms.decomposition.analysis` |
| `post_v1_mechanisms.cli` | `studies.mechanisms.decomposition.cli` |
| `probes` | `core.probes` |
| `random10_report` | `reporting.random10` |
| `relation_signal_causal_transfer` | `studies.calibration.relation_signal_transfer` |
| `report_runtime` | `reporting.runtime` |
| `reporting` | `reporting.notebooks` |
| `response_anchoring` | `audits.response_anchoring` |
| `response_audit` | `audits.response_semantics` |
| `retry` | `core.retry` |
| `router` | `core.router` |
| `semantic_ecology` | `studies.ecology.semantic_ecology` |
| `theory_v1.__main__` | `studies.theory.v1.__main__` |
| `theory_v1.cli` | `studies.theory.v1.cli` |
| `theory_v1.dynamics` | `studies.theory.v1.dynamics` |
| `theory_v1.ecologies` | `studies.theory.v1.ecologies` |
| `theory_v1.forensic_repair` | `studies.theory.v1.forensic_repair` |
| `theory_v1.macro_runner` | `studies.theory.v1.macro_runner` |
| `theory_v1.micro_analysis` | `studies.theory.v1.micro_analysis` |
| `theory_v1.micro_design` | `studies.theory.v1.micro_design` |
| `theory_v1.micro_estimation` | `studies.theory.v1.micro_estimation` |
| `theory_v1.micro_runner` | `studies.theory.v1.micro_runner` |
| `theory_v1.prediction` | `studies.theory.v1.prediction` |
| `theory_v1.scorecard` | `studies.theory.v1.scorecard` |
| `theory_v1.scoring` | `studies.theory.v1.scoring` |
| `theory_v1_1` | `studies.theory.v1_1.replication` |
| `theory_v1_1_analysis` | `studies.theory.v1_1.analysis` |
| `theory_v1_1_macro` | `studies.theory.v1_1.macro` |
| `theory_v1_1_predictions` | `studies.theory.v1_1.predictions` |
| `transfer_analysis` | `studies.ecology.transfer_analysis` |
| `transfer_geometry` | `studies.ecology.transfer_geometry` |
| `transfer_operator` | `studies.ecology.transfer_operator` |
Unchanged: `metrics.*`, `providers.{base,deepseek_direct,mock,omp_rpc}`.

Console scripts (`emergent-specialization`, `emergence-report`,
`emergence-compare`, `emergence-credentials`) are unchanged; only their
underlying entry points moved.
