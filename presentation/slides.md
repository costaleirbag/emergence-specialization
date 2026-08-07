---
theme: default
title: Emergent Specialization
info: Routing, symmetry breaking, and differentiation in an LLM society
class: text-left
highlighter: shiki
transition: fade
mdc: true
css: unocss
---
<style>
@import './styles.css';
</style>

# Emergent Specialization

## Can routing generate the diversity it exploits?

An exploratory research update · LLM societies · 06 Aug 2026

<div class="rule"></div>
<p class="subtitle">A systems experiment on symmetry breaking, feedback, and functional differentiation.</p>

<div class="footer-note">Mestrado · research talk · preliminary evidence, not a causal conclusion</div>

<!-- presenter notes: Open with the question, not the implementation. This is a story that began with a routing paper and became a question about emergence. -->

---

# The paper that triggered the idea

<div class="grid-2">
<div>
<div class="eyebrow">Starting point</div>
<h2>When is routing meaningful?</h2>
<p>The motivating paper asks when a router does more than exploit arbitrary behavioral diversity in a language-model society.</p>
<p class="muted">Its useful provocation: diversity is not automatically valuable. It matters when routing can reliably match tasks to different competencies.</p>
</div>
<div class="panel">
<div class="eyebrow">The implicit assumption</div>
<div class="quote">Routing assumes that there is something meaningfully different to route between.</div>
<p class="small muted">That left an open systems question: where does the diversity come from?</p>
</div>
</div>

<!-- presenter notes: Briefly situate the paper as the intellectual trigger. Do not claim it proposed this exact experiment; this project is the question that followed. -->

---

# The question that changed the direction

<div class="hero">
<div class="eyebrow">A conversation, not a finished theory</div>
<h1>What if the actors<br><span class="private">start identical?</span></h1>
<div class="quote">Does routing merely exploit diversity,<br>or can routing generate the diversity it exploits?</div>
<p class="muted" style="margin-top:1.2rem">The project turns a descriptive routing question into a dynamical-systems question.</p>
</div>

<!-- presenter notes: Pause after the quote. This is the central transition in the talk. -->

---

# Core hypothesis

<div class="grid-2" style="align-items:center">
<div><div class="eyebrow">Hypothesis</div><h1>Selection + asymmetric feedback can break symmetry.</h1></div>
<div class="panel">
<p>Initially exchangeable agents may accumulate different histories.</p>
<div class="flow">
<div class="step"><b>same start</b><br><span class="muted small">same model, prompt, tools</span></div>
<div class="step"><b>different draw</b><br><span class="muted small">confidence breaks a tie</span></div>
<div class="step"><b>different history</b><br><span class="muted small">one agent gets feedback</span></div>
</div>
<p class="small muted">The claim is deliberately conditional: differentiation may emerge, but it may also collapse or remain unhelpful.</p>
</div>
</div>

<!-- presenter notes: Emphasize that “symmetry breaking” is a mechanism hypothesis, not an observation already proven by this run. -->

---

# A complex-systems intuition

<div class="nodes">
<div class="node">exchangeable<br>agents</div><div style="font-size:2rem;color:var(--teal)">→</div>
<div class="node">stochastic<br>fluctuation</div><div style="font-size:2rem;color:var(--teal)">→</div>
<div class="node">feedback<br>asymmetry</div><div style="font-size:2rem;color:var(--teal)">→</div>
<div class="node">persistent<br>organization?</div>
</div>
<div class="panel" style="margin-top:2rem"><b>Important distinction</b><p class="small">A structured routing pattern can be a transient fluctuation, a collapse onto one agent, or useful specialization. The experiment must separate these possibilities.</p></div>

<!-- presenter notes: This slide gives the intuition without invoking a phase transition. The observable is a trajectory, not a single end-state score. -->

---

# Experimental goal

<div class="hero">
<div class="eyebrow">Question made operational</div>
<h1>Can initially homogeneous agents diverge functionally?</h1>
<div class="grid-3" style="margin-top:1.5rem">
<div class="panel"><b>Organization</b><p class="small">Does routing become world-structured?</p></div>
<div class="panel"><b>Competence</b><p class="small">Does any structure align with correctness?</p></div>
<div class="panel"><b>Control</b><p class="small">Does private feedback matter relative to shared feedback?</p></div>
</div>
</div>

<!-- presenter notes: The causal comparison is private versus shared. A single private run can show patterns, but cannot identify the feedback mechanism. -->

---

# Initial conditions: deliberately boring

<div class="grid-2">
<div class="panel"><div class="eyebrow">All agents begin exchangeable</div><ul class="tight"><li>same DeepSeek V4 Flash model</li><li>same system prompt</li><li>same task interface</li><li>no manually assigned roles</li><li>same confidence router</li></ul></div>
<div class="panel"><div class="eyebrow">What is controlled by Python</div><ul class="tight"><li>memory strategy: <code>recent_k</code>, k = 8</li><li>feedback recipient(s)</li><li>task generation and hidden answer</li><li>fresh OMP session per completion</li><li>probe evaluation at fixed checkpoints</li></ul></div>
</div>
<p class="muted small" style="margin-top:1rem">The model does not carry an uncontrolled conversation between calls; experimental history is host-side.</p>

<!-- presenter notes: This is the anti-confound slide. “Homogeneous” means no assigned role, not identical token-by-token behavior. -->

---

# Four hidden worlds, one task interface

<div class="grid-4" style="margin-top:2rem">
<div class="panel center"><div class="big-number">α</div><h3>ALPHA</h3><p class="small">stable hidden rule</p></div>
<div class="panel center"><div class="big-number" style="color:var(--amber)">β</div><h3>BETA</h3><p class="small">stable hidden rule</p></div>
<div class="panel center"><div class="big-number" style="color:var(--pink)">γ</div><h3>GAMMA</h3><p class="small">stable hidden rule</p></div>
<div class="panel center"><div class="big-number" style="color:var(--blue)">δ</div><h3>DELTA</h3><p class="small">stable hidden rule</p></div>
</div>
<div class="grid-2" style="margin-top:1.6rem"><div><b>Same surface task</b><p class="small">Given a world and x, y, return an answer in {0,…,6} plus confidence.</p></div><div><b>Why synthetic?</b><p class="small">Known ground truth, modular rules, and no dependence on pretraining knowledge.</p></div></div>

<!-- presenter notes: The worlds make correctness deterministic and let us ask whether routing aligns with hidden task structure. -->

---

# One round of the experiment

<div class="flow" style="margin-top:2.4rem">
<div class="step"><div class="eyebrow">01 · broadcast</div><h3>same task</h3><p class="small">All four agents see the current world and input.</p></div>
<div class="step"><div class="eyebrow">02 · infer</div><h3>answer + confidence</h3><p class="small">Each isolated completion returns structured JSON.</p></div>
<div class="step"><div class="eyebrow">03 · route</div><h3>argmax confidence</h3><p class="small">The confidence router selects one candidate.</p></div>
<div class="step"><div class="eyebrow">04 · learn</div><h3>feedback</h3><p class="small">Correct answer becomes an Experience for selected recipient(s).</p></div>
</div>
<div class="quote" style="margin-top:1.6rem">One selection changes the future information available to the society.</div>

<!-- presenter notes: Explain that routing is not just a readout: it controls who receives the next piece of supervised information. -->

---

# Private vs shared: the causal control

<div class="grid-2">
<div class="panel" style="border-top:3px solid var(--teal)"><div class="eyebrow private">PRIVATE</div><h2>selected agent only</h2><p>The selected agent receives the round’s Experience. The other three memories remain unchanged.</p><div class="big-number">1</div><p class="small muted">feedback recipient</p></div>
<div class="panel" style="border-top:3px solid var(--amber)"><div class="eyebrow shared">SHARED</div><h2>everyone receives it</h2><p>The same feedback is copied to all agents, removing the information asymmetry.</p><div class="big-number" style="color:var(--amber)">4</div><p class="small muted">feedback recipients</p></div>
</div>
<p class="muted small" style="margin-top:1rem">The shared run was not complete when this deck was generated; no comparison is fabricated here.</p>

<!-- presenter notes: This is the key experimental control. If the shared run is later complete, regenerate data and this section can become a direct comparison. -->

---

# The feedback loop

<div class="nodes" style="margin-top:1.8rem"><div class="node">experience<br>in memory</div><div style="font-size:2rem;color:var(--teal)">→</div><div class="node">competence<br>and confidence</div><div style="font-size:2rem;color:var(--teal)">→</div><div class="node">selection<br>probability</div><div style="font-size:2rem;color:var(--teal)">→</div><div class="node">more / less<br>experience</div></div>
<div class="panel" style="margin:2rem auto 0;max-width:850px"><p class="center">This is a positive-feedback hypothesis. It can amplify useful specialization—or amplify early mistakes and collapse.</p></div>

<!-- presenter notes: Point out the two possible directions: productive division of labor and pathological rich-get-richer dynamics. -->

---

# What counts as “specialization”?

<div class="grid-4">
<MetricCard label="HSE" value="behavioral" detail="Are agents behaviorally different?" accent="teal" />
<MetricCard label="Task ↔ agent MI" value="organization" detail="Is routing world-structured?" accent="blue" />
<MetricCard label="Utilization entropy" value="balance" detail="Is usage concentrated or spread?" accent="amber" />
<MetricCard label="Oracle gain" value="complementarity" detail="Does the society beat its best agent?" accent="pink" />
</div>
<div class="quote" style="margin-top:1.7rem">No single metric is sufficient. Diversity ≠ useful specialization.</div>
<p class="small muted">High routing concentration can mean collapse. MI can indicate organization without competence. HSE can be high before any useful division of labor exists.</p>

<!-- presenter notes: This is where we guard against Goodhart-style interpretation. The independent outcome is competence and complementarity, not HSE alone. -->

---

# Implementation snapshot

<div class="grid-3">
<div class="panel"><div class="eyebrow">Model path</div><h3>DeepSeek V4 Flash</h3><p class="small">OMP RPC backend · thinking off · fresh <code>--no-session</code> process per completion.</p></div>
<div class="panel"><div class="eyebrow">Run design</div><h3>4 × 20 + probes</h3><p class="small">80 interaction calls plus 320 common-probe calls at t = 0 and t = 20.</p></div>
<div class="panel"><div class="eyebrow">Reproducibility</div><h3>seed 1 · fixed probes</h3><p class="small">Probe hash <code>{{ p.probe_set_hash?.slice(0, 12) }}</code> · private memory · epsilon = 0.</p></div>
</div>
<div class="panel" style="margin-top:1.5rem"><b>What the probes do</b><p class="small">At checkpoints, all agents answer the same 40 probes. These diagnostics are expensive model calls and do not update experimental memory.</p></div>

<!-- presenter notes: Separate online interaction dynamics from sparse diagnostic probing. This matters for cost and for future trajectory work. -->

---

# Results · PRIVATE overview

<div class="eyebrow">latest completed run · {{ p.run_id }}</div>
<div class="grid-4" style="margin-top:1.1rem">
<MetricCard label="Best individual" :value="pct(f.best_individual_accuracy)" detail="agent_1" accent="teal" />
<MetricCard label="Oracle society" :value="pct(f.oracle_society_accuracy)" detail="best agent per world" accent="blue" />
<MetricCard label="Oracle gain" :value="pct(f.oracle_gain)" detail="complementarity signal" accent="pink" />
<MetricCard label="HSE / MI / util." :value="`${num(f.normalized_hse)} / ${num(f.normalized_task_agent_mutual_information)} / ${num(f.normalized_utilization_entropy)}`" detail="normalized final metrics" accent="amber" />
</div>
<div class="grid-3" style="margin-top:1.3rem"><div class="panel"><b>Routing</b><p class="small">agent_1: 17 · agent_2: 2 · agent_0: 1</p></div><div class="panel"><b>Memory</b><p class="small">agent_1: 17 · agent_2: 2 · agent_0: 1</p></div><div class="panel"><b>Runtime health</b><p class="small">{{ p.event_stats.inference_attempts }} attempts · {{ p.event_stats.errors }} errors · {{ p.event_stats.timeouts }} timeouts</p></div></div>
<p class="small muted" style="margin-top:.9rem">Usage coverage: {{ pct(p.event_stats.usage.coverage) }} · recorded cost: ${{ p.event_stats.usage.cost_usd?.toFixed(4) }} · wall-clock sum of inference latencies: {{ mins(p.event_stats.latency.total_s) }}</p>

<!-- presenter notes: This is a descriptive snapshot. Call out the heavy agent_1 routing concentration and the timeout caveat before interpreting metrics. -->

---

# PRIVATE · routing matrix

<p class="muted">Selected agent counts over the 20 interaction rounds, by hidden world.</p>
<HeatmapTable :rows="worlds" :columns="agents" :values="routing" :digits="0" />
<div class="grid-2" style="margin-top:1.1rem"><div class="panel"><b>Visible structure</b><p class="small">agent_1 receives 17/20 selections, including all 3 BETA selections and 7/8 DELTA selections.</p></div><div class="panel"><b>Interpretation guardrail</b><p class="small">Concentration is not automatically specialization. It can be router collapse or confidence calibration.</p></div></div>

<!-- presenter notes: Read the matrix as a routing pattern, not as proof of competence. The imbalance is the central empirical fact of this run. -->

---

# PRIVATE / competence matrix

<p class="muted">Accuracy on the 40 common probes at checkpoint t = 20.</p>
<HeatmapTable :rows="agents" :columns="worlds" :values="Object.fromEntries(agents.map(a => [a, f.competence_matrix?.[a] || {}]))" />
<div class="grid-2" style="margin-top:1.1rem"><div class="panel"><b>Strongest alignment</b><p class="small">agent_1 is highly accurate on BETA (1.00) and is also heavily selected on BETA.</p></div><div class="panel"><b>Partial complementarity</b><p class="small">agent_3 is the strongest GAMMA probe performer (0.40), but receives no interaction routing in the final matrix.</p></div></div>

<!-- presenter notes: This is the most interesting alignment and misalignment slide. BETA supports useful routing; GAMMA shows why routing and competence must be examined together. -->

---

# PRIVATE · checkpoint dynamics

<ComparisonTable :rows="[
  {label:'best individual accuracy', start:pct(cp0.best_individual_accuracy), end:pct(cp20.best_individual_accuracy), reading:'improved, but one checkpoint'},
  {label:'oracle society accuracy', start:pct(cp0.oracle_society_accuracy), end:pct(cp20.oracle_society_accuracy), reading:'complementary capability'},
  {label:'normalized HSE', start:num(cp0.normalized_hse), end:num(cp20.normalized_hse), reading:'behavioral separation increased'},
  {label:'task ↔ agent MI', start:num(cp0.normalized_task_agent_mutual_information), end:num(cp20.normalized_task_agent_mutual_information), reading:'organization emerged from zero'},
  {label:'utilization entropy', start:num(cp0.normalized_utilization_entropy), end:num(cp20.normalized_utilization_entropy), reading:'from no routing history to concentration'}
 ]" />
<p class="small muted" style="margin-top:1rem">The t = 0 HSE value is a stochastic baseline from common-probe behavior. A rise in HSE alone does not establish useful specialization.</p>

<!-- presenter notes: Stress that two checkpoints are not a trajectory study. The change is suggestive and descriptive, not a temporal law. -->

---

# What can we say about this PRIVATE run?

<div class="grid-2">
<div class="panel"><div class="eyebrow good">Supported by artifacts</div><ul class="tight"><li>routing became strongly concentrated on agent_1</li><li>agent_1’s BETA competence aligned with BETA routing</li><li>agent_3 had the best GAMMA competence, but was not selected there</li><li>the society’s oracle accuracy exceeded its best individual</li></ul></div>
<div class="panel"><div class="eyebrow warning">Still unresolved</div><ul class="tight"><li>one seed cannot establish an emergent regime</li><li>concentration may be confidence/router collapse</li><li>13 timeouts and retries affect operational reliability</li><li>private-only data cannot identify the feedback effect</li></ul></div>
</div>
<div class="quote" style="margin-top:1.3rem">Preliminary evidence of organized differentiation? Plausible. Proof of emergent specialization? Not yet.</div>

<!-- presenter notes: This is the honest conclusion slide. Use “plausible” and “not yet” deliberately. -->

---

# The SHARED control is still pending

<div class="hero center"><div class="eyebrow shared">No invented comparison</div><div class="big-number" style="font-size:6rem;color:var(--amber)">—</div><h1>Shared run incomplete<br>when this deck was generated.</h1><p class="muted">The presentation is data-driven: regenerate <code>presentation-data.json</code> after a completed shared run and populate the comparison slides without changing the narrative.</p></div>

<!-- presenter notes: If shared has completed before the talk, regenerate the data and replace this slide with the comparison. Until then, say explicitly that the causal control is pending. -->

---

# Why the result is interesting anyway

<div class="grid-3">
<div class="panel"><div class="eyebrow">Routing</div><h3>Structure can appear</h3><p class="small">The selected agent is not uniformly distributed across the society.</p></div>
<div class="panel"><div class="eyebrow">Emergence</div><h3>History is a state variable</h3><p class="small">Private feedback makes information access endogenous to selection.</p></div>
<div class="panel"><div class="eyebrow">Measurement</div><h3>Organization ≠ competence</h3><p class="small">The matrix mismatch is as informative as the alignment.</p></div>
</div>
<p class="quote" style="margin-top:1.8rem">The contribution, for now, is a falsifiable experimental setup—not a claim that one run discovered a new phase.</p>

<!-- presenter notes: Link back to the motivating paper and to complex systems: the same feedback process can create order or failure. -->

---

# Limitations before interpretation

<div class="two-col"><ul class="tight"><li>single completed seed shown here</li><li>20 interaction rounds</li><li>synthetic hidden worlds</li><li>confidence router may amplify calibration artifacts</li><li>probe metrics are sparse and expensive</li></ul><ul class="tight"><li>timeouts: {{ p.event_stats.timeouts }}</li><li>retries: {{ p.event_stats.retries }}</li><li>usage not complete for every attempt</li><li>shared control not yet available</li><li>no claim about generalization outside this harness</li></ul></div>
<div class="panel" style="margin-top:1.3rem"><b>Methodological consequence</b><p class="small">The next decision should be driven by technical health and matched design—not by whether the private metrics look impressive.</p></div>

<!-- presenter notes: This slide keeps the group from treating the preliminary result as a victory lap. -->

---

# Next steps: make the comparison decisive

<div class="flow"><div class="step"><div class="eyebrow">01</div><b>finish matched SHARED</b><p class="small">same seed, probes, model, commit</p></div><div class="step"><div class="eyebrow">02</div><b>repeat seeds</b><p class="small">estimate stochastic variation</p></div><div class="step"><div class="eyebrow">03</div><b>add controls</b><p class="small">no-memory and routing baselines</p></div><div class="step"><div class="eyebrow">04</div><b>study trajectories</b><p class="small">cheap online signals + sparse probes</p></div></div>
<p class="muted small">Only later: topology, outer-loop design, and closed-loop intervention. The baseline must remain stable first.</p>

<!-- presenter notes: Keep the order. The private/shared pair is the immediate scientific priority; trajectory prediction is future work. -->

---

# Final takeaway

<div class="hero"><div class="eyebrow">The question to carry forward</div><h1>Routing may be more than a selector.</h1><div class="quote">It may participate in creating the differentiated society it later routes through.</div><p class="muted" style="margin-top:1.1rem">Our first private run shows the pattern is measurable. The shared control and repeated seeds will tell us whether it is causal, robust, and useful.</p></div>

<!-- presenter notes: End by returning to the original question. The next experiment, not this slide, decides the claim. -->

---

# Backup · run card

<div class="grid-2"><div class="panel"><div class="eyebrow">Selected artifact</div><h3>{{ p.run_id }}</h3><p class="small">{{ p.directory }}</p><p class="small">run git provenance: <code>{{ p.git_head || 'not recorded' }}</code></p><p class="small">probe hash: <code>{{ p.probe_set_hash }}</code></p></div><div class="panel"><div class="eyebrow">Configuration</div><p class="small">{{ p.config.agents }} agents · {{ p.config.rounds }} rounds · checkpoints {{ p.config.checkpoints }}</p><p class="small">{{ p.config.model }} · {{ p.config.backend }} · {{ p.config.memory_mode }} memory</p><p class="small">{{ p.config.router }} router · ε={{ p.config.epsilon }} · thinking {{ p.config.thinking }}</p></div></div>

<!-- presenter notes: Use this slide if someone asks about exact provenance. -->

---

# Backup · definitions

<div class="grid-2"><div class="panel"><b>HSE</b><p class="small">A behavioral specialization/diversity statistic computed from common-probe response profiles.</p><b>Task–agent MI</b><p class="small">Mutual information between worlds/tasks and selected agents; organization, not competence.</p></div><div class="panel"><b>Utilization entropy</b><p class="small">How evenly routing load is distributed across agents.</p><b>Oracle gain</b><p class="small">Oracle society accuracy minus the best individual accuracy; a complementarity signal.</p></div></div>
<p class="small muted" style="margin-top:1.2rem">All are observables in a measurement stack. The terminal objective must remain independently meaningful.</p>

<!-- presenter notes: This is a glossary, not a new result. -->
