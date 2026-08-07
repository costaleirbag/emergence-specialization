---
theme: frankfurt
layout: cover
infoLine: true
topNavigation: true
author: Research group
title: Emergent Specialization in Homogeneous LLM Societies
date: 2026/08/06
info: Routing, symmetry breaking, and differentiation in an LLM society
transition: fade
mdc: true
---

<style>
@import './styles.css';
</style>

# Emergent Specialization<br>in Homogeneous LLM Societies

Can routing generate the diversity it later exploits?

<div class="cover-meta">Research update · LLM societies · Mestrado · 06 Aug 2026</div>

<!-- presenter notes: Begin with the question. This talk follows an idea from a routing paper to a controlled experiment about differentiation. -->

---
layout: intro
section: Origin
---

<div class="eyebrow">The trigger</div>

# From routing to emergence

## A routing paper

Behavioral diversity is useful only when a router can match tasks to different competencies.

<Item title="The question it left behind">Where does the diversity come from in the first place?</Item>

<!-- presenter notes: The paper is the starting point, not a claim that it proposed this exact experiment. -->

---
layout: intro
---

<div class="academic-center">

# What if the actors start identical?

<p class="quote-attribution">A question that changed the direction of the project.</p>

</div>

<!-- presenter notes: Let the question breathe. This is the conceptual pivot. -->

---
layout: intro
---

<div class="academic-center central-question">

# Does routing merely exploit diversity,<br>or can it generate the diversity it exploits?

</div>

<!-- presenter notes: State the central hypothesis exactly. -->

---
layout: intro
section: Emergence
---

# From symmetry

## Same start

Same model · same prompt · same interface

## A possible divergence

Fluctuation → asymmetric feedback → different histories

<!-- presenter notes: Avoid calling this a phase transition. It is a mechanism hypothesis about feedback and histories. -->

---

# Initial symmetry

<div class="item-grid four">
<Item title="agent 0">exchangeable</Item>
<Item title="agent 1">exchangeable</Item>
<Item title="agent 2">exchangeable</Item>
<Item title="agent 3">exchangeable</Item>
</div>

<div class="items-caption">empty controlled memory · no predefined roles · same confidence router</div>

<!-- presenter notes: Homogeneous means no assigned role or privileged history—not identical token-level behavior. -->

---
layout: intro
section: Experiment
---

# The experiment

## Goal

Test whether initially homogeneous agents can diverge functionally.

## Control

Private feedback versus shared feedback.

<!-- presenter notes: A private run alone is descriptive. The matched shared condition is the causal control. -->

---

# Four hidden worlds, one task interface

<div class="world-grid">
<div><b>ALPHA</b><span>α</span></div><div><b>BETA</b><span>β</span></div><div><b>GAMMA</b><span>γ</span></div><div><b>DELTA</b><span>δ</span></div>
</div>

<div class="brick-row">
<div><b>Surface task</b><br><small>world + x + y → answer in {0,…,6} + confidence</small></div>
<div><b>Why synthetic?</b><br><small>deterministic ground truth and no pretraining-knowledge confound</small></div>
</div>

<!-- presenter notes: The worlds create modular hidden rules with known correctness. -->

---

# One round of the society

<div class="round-flow">
<div><span>01</span><b>Broadcast</b><small>same task to all agents</small></div>
<div><span>02</span><b>Infer</b><small>answer + confidence</small></div>
<div><span>03</span><b>Route</b><small>argmax confidence</small></div>
<div><span>04</span><b>Feedback</b><small>selected recipient(s)</small></div>
</div>

<p class="small-note">Memory is controlled by Python; each OMP completion uses a fresh isolated session.</p>

<!-- presenter notes: Routing controls who receives supervised information, so it is part of the dynamics rather than just a readout. -->

---

# Private versus shared

<div class="compare-grid">
<div class="compare private-side"><div class="eyebrow">PRIVATE</div><h2>selected agent only</h2><p>Feedback enters one controlled memory.</p><div class="arrow-stack">selected<br>↓<br>one memory<br>↓<br>histories diverge</div></div>
<div class="compare shared-side"><div class="eyebrow">SHARED</div><h2>feedback broadcast</h2><p>The same Experience enters every memory.</p><div class="arrow-stack">selected<br>↓<br>four memories<br>↓<br>histories remain aligned</div></div>
</div>

<p class="small-note">The matched shared run was incomplete when this deck was generated.</p>

<!-- presenter notes: This is the key causal contrast. Do not interpret the private run as proof without the shared control. -->

---
layout: intro
---

<div class="academic-center feedback-loop">

# experience → competence → confidence → routing → more experience

<p class="quote-attribution">A positive-feedback loop that may amplify useful specialization—or early mistakes.</p>

</div>

<!-- presenter notes: Explain both possible regimes: productive division of labor and confidence-driven collapse. -->

---

# What counts as specialization?

<div class="item-grid four">
<Item title="HSE">Are agents behaviorally different?</Item>
<Item title="I(C;R)">Is routing organized by task?</Item>
<Item title="Utilization">Did routing collapse?</Item>
<Item title="Oracle gain">Are differences useful?</Item>
</div>

<div class="items-caption">Diversity ≠ useful specialization · no single metric is sufficient</div>

<!-- presenter notes: HSE is a candidate observable, not the objective. MI can show organization without competence; concentration can be collapse. -->

---
layout: intro
section: Results
---

# What happened?

## Latest completed PRIVATE run

{{ p.run_id }}

## 4 agents · 20 rounds

80 interaction calls + 320 probe calls

<!-- presenter notes: Introduce the actual artifact before showing its matrices. The shared control is intentionally not filled in. -->

---
layout: intro
---

<div class="academic-center result-fact">

# {{ pct(f.best_individual_accuracy) }}

Best individual accuracy at t = 20

</div>

<!-- presenter notes: This is a descriptive fact from the common-probe evaluation, not a generalization claim. -->

---

# PRIVATE · terminal observables

<div class="fact-grid">
<div><strong>{{ pct(f.oracle_society_accuracy) }}</strong><small>oracle society accuracy</small></div>
<div><strong>{{ pct(f.oracle_gain) }}</strong><small>oracle gain</small></div>
<div><strong>{{ num(f.normalized_hse) }}</strong><small>normalized HSE</small></div>
<div><strong>{{ num(f.normalized_task_agent_mutual_information) }}</strong><small>normalized task ↔ agent MI</small></div>
</div>

<p class="small-note">Utilization entropy: {{ num(f.normalized_utilization_entropy) }} · agent_1 selected 17/20 rounds</p>

<!-- presenter notes: Read these as a measurement stack. The oracle improvement is the complementarity signal; the routing concentration needs a control. -->

---

# PRIVATE · routing matrix

<p class="small-note">Selected agent counts across the 20 interaction rounds.</p>
<HeatmapTable :rows="worlds" :columns="agents" :values="routing" :digits="0" />

<div class="brick-row compact"><div><b>Concentration</b><br><small>agent_1 receives 17/20 selections</small></div><div><b>Guardrail</b><br><small>concentration can be collapse, not specialization</small></div></div>

<!-- presenter notes: The routing pattern is highly asymmetric. Show it as a fact, not as a causal explanation. -->

---

# PRIVATE · competence matrix

<p class="small-note">Accuracy on the 40 common probes at checkpoint t = 20.</p>
<HeatmapTable :rows="agents" :columns="worlds" :values="Object.fromEntries(agents.map(a => [a, f.competence_matrix?.[a] || {}]))" />

<div class="brick-row compact"><div><b>Alignment</b><br><small>agent_1 is perfect on BETA and heavily selected there</small></div><div><b>Mismatch</b><br><small>agent_3 leads GAMMA but receives no final routing there</small></div></div>

<!-- presenter notes: This alignment/mismatch is why routing and competence must be shown together. -->

---

# PRIVATE · checkpoint dynamics

<ComparisonTable :rows="[
  {label:'best individual', start:pct(cp0.best_individual_accuracy), end:pct(cp20.best_individual_accuracy), reading:'improved'},
  {label:'oracle society', start:pct(cp0.oracle_society_accuracy), end:pct(cp20.oracle_society_accuracy), reading:'complementarity'},
  {label:'normalized HSE', start:num(cp0.normalized_hse), end:num(cp20.normalized_hse), reading:'separation increased'},
  {label:'task ↔ agent MI', start:num(cp0.normalized_task_agent_mutual_information), end:num(cp20.normalized_task_agent_mutual_information), reading:'organization from zero'},
  {label:'utilization entropy', start:num(cp0.normalized_utilization_entropy), end:num(cp20.normalized_utilization_entropy), reading:'concentration'}
 ]" />

<p class="small-note">Two checkpoints are not a trajectory study. t = 0 HSE is a stochastic baseline.</p>

<!-- presenter notes: Avoid extrapolating monotonic emergence from two observations. -->

---
layout: intro
---

<div class="academic-center result-fact wide">

# The society’s oracle reaches {{ pct(f.oracle_society_accuracy) }}

while the best individual reaches {{ pct(f.best_individual_accuracy) }}

</div>

<!-- presenter notes: Oracle gain is evidence of complementary capability in the probe set, not evidence that the router actually found the best agent on every task. -->

---

# What can we say now?

<div class="brick-row">
<div><div class="eyebrow">Supported</div><ul><li>routing is strongly concentrated</li><li>BETA routing aligns with agent_1 competence</li><li>oracle society exceeds the best individual</li></ul></div>
<div><div class="eyebrow">Unresolved</div><ul><li>one seed cannot establish a regime</li><li>GAMMA shows routing/competence mismatch</li><li>private-only data cannot identify the feedback effect</li></ul></div>
</div>

<p class="small-note">Preliminary evidence of organized differentiation? Plausible. Proof of emergent specialization? Not yet.</p>

<!-- presenter notes: This is the honest interpretation. -->

---
layout: intro
section: Interpretation
---

<div class="academic-center">

# The SHARED control is still pending

<p class="statement-sub">No comparison is fabricated. Regenerate the data after a completed shared run.</p>

</div>

<!-- presenter notes: If the shared run finishes before the talk, rerun npm run data and replace this slide with the real comparison. -->

---
layout: intro
section: Next steps
---

# What remains

## Immediate

Matched PRIVATE / SHARED on the same seed and commit.

## Then

More seeds · no-memory control · routing baselines.

## Later

Trajectory prediction, topology, and intervention.

<!-- presenter notes: Keep the order. The matched control is the next scientific priority. -->

---

# Limitations

<div class="item-grid four">
<Item title="1 seed">stochastic variation unknown</Item>
<Item title="20 rounds">short horizon</Item>
<Item title="Synthetic worlds">controlled but narrow</Item>
<Item title="Timeouts">{{ p.event_stats.timeouts }} in this run</Item>
</div>

<div class="items-caption">The next decision should follow technical health and matched design—not attractive metrics.</div>

<!-- presenter notes: Make the limitations explicit before taking questions. -->

---
layout: intro
---

<div class="academic-center">

# Routing may do more than select.

<p class="statement-sub">It may help create the differentiated society it later routes through.</p>
<p class="small-note">The private/shared control tells us whether that mechanism is causal.</p>

</div>

<!-- presenter notes: Return to the opening question. The next matched experiment decides the claim. -->

---
section: Backup
---

# Backup · provenance

<div class="brick-row">
<div><b>Run</b><br><small>{{ p.run_id }}</small><br><small>{{ p.directory }}</small></div>
<div><b>Configuration</b><br><small>{{ p.config.agents }} agents · {{ p.config.rounds }} rounds · checkpoints {{ p.config.checkpoints }}</small><br><small>{{ p.config.model }} · {{ p.config.backend }} · {{ p.config.memory_mode }} memory</small></div>
</div>
<div class="brick-row compact"><div><b>Probe hash</b><br><small>{{ p.probe_set_hash }}</small></div><div><b>OMP</b><br><small>{{ p.backend.version }} · {{ p.backend.session_policy }}</small></div></div>

<!-- presenter notes: Use this slide for exact provenance questions. -->

---

# Backup · measurement glossary

<div class="brick-row">
<div><b>HSE</b><br><small>behavioral separation on common probes</small><br><br><b>Task ↔ agent MI</b><br><small>organization of routing by world</small></div>
<div><b>Utilization entropy</b><br><small>how evenly routing load is distributed</small><br><br><b>Oracle gain</b><br><small>complementarity over the best individual</small></div>
</div>

<p class="small-note">All are observables. The terminal objective must remain independently meaningful.</p>

<!-- presenter notes: These are definitions, not additional claims. -->
