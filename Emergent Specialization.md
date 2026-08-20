# Emergent Specialization in Initially Homogeneous LLM Societies

> **Status:** experimental plan / pilot  
> **Goal:** build a small, controlled multi-agent experiment in which initially identical LLM agents may develop persistent functional differentiation through asymmetric interaction histories, and measure that differentiation using metrics inspired by *When is Routing Meaningful? Diversity and Robustness in Language Model Societies*.

---

## 0. Executive summary

The paper *When is Routing Meaningful?* asks whether a routing system is structurally meaningful when:

1. the available actors are behaviorally diverse; and
2. the router makes stable decisions under semantically equivalent perturbations.

The paper treats behavioral diversity mostly as a **static property** of a given society and measures it using **Hierarchic Social Entropy (HSE)**.

This project asks the inverse, dynamical question:

> **Can behavioral diversity and functional specialization emerge from a society of initially identical language-model agents through asymmetric interaction histories alone?**

We start with $N$ copies of the **same model**, with the same system prompt, capabilities, initial memory, task distribution, and no manually assigned roles.

The only mechanism allowed to break the symmetry is the history of interaction:

```math
r_i(0) \equiv r_j(0)
\qquad \forall i,j,
```

but after agents receive different private feedback,

```math
m_i(t) \neq m_j(t),
```

so their effective behavior may diverge.

The core experiment compares:

- **Shared-memory society:** every feedback item is visible to every agent.
- **Private-memory society:** only the selected agent receives feedback.

At fixed checkpoints we freeze the society, evaluate every agent on the same probe set, construct the behavioral matrix $B(t)$, and measure:

- HSE through time;
- mutual information between task domain and selected agent;
- utilization entropy;
- complementary competence / oracle gain;
- routing robustness;
- temporal stability of emergent roles.

The desired pilot result is **not** “we discovered a phase transition.” The target is narrower:

> Under controlled conditions, asymmetric histories can amplify initially microscopic differences into persistent behavioral differentiation and task-dependent routing patterns.

---

# 1. Research question

## Primary question

> **Can functional diversity emerge in a society of initially identical LLM agents when the agents share weights and initial instructions but accumulate different private experiences?**

Suppose the agents are initially exchangeable:

```math
\mathcal R(0) = \{r_1(0),\ldots,r_N(0)\},
```

with

```math
r_i(0) \overset{\text{behavior}}{\approx} r_j(0)
\qquad \forall i,j.
```

We expose the society to a sequence of tasks

```math
q_1,q_2,\ldots,q_T,
```

and allow the interaction mechanism to generate different histories $m_i(t)$. We then ask whether the induced behavioral profiles $b_i(t)$ become measurably different over time.

## Secondary questions

1. Does behavioral diversity increase over time?
2. Does this diversity correspond to useful specialization, or merely arbitrary divergence?
3. Does a stable mapping emerge between task type and agent identity?
4. Are emergent routing decisions robust to semantically irrelevant perturbations?
5. Does the society develop complementary competence that exceeds the best individual agent?
6. Is the effect absent or substantially weaker when feedback is shared?
7. Are emergent roles persistent, or do agents continually exchange functions?

---

# 2. Connection to the routing paper

The routing paper evaluates each actor on a common task set

```math
\mathcal E=\{e_1,\ldots,e_L\},
```

and gives each actor a behavioral vector

```math
b_i =
\left(
s(r_i,e_1),
\ldots,
s(r_i,e_L)
\right).
```

Stacking them gives

```math
B=
\begin{bmatrix}
b_1^\top\\
\vdots\\
b_N^\top
\end{bmatrix}.
```

The conceptual extension here is simply:

```math
\boxed{B \rightarrow B(t)}
```

We construct the same object at several time checkpoints and study the trajectory of the society.

### Paper

> Given actors that may already differ, how behaviorally diverse is the society?

### This experiment

> Given actors that initially do **not** differ, can interaction dynamically generate the behavioral diversity that HSE later detects?

This turns HSE from a static diagnostic into a possible **order parameter for differentiation**.

---

# 3. What we mean by “emergence”

For this pilot, “emergent specialization” means:

> Persistent task-dependent behavioral differentiation that was **not manually assigned in the initial conditions** and that arises through the interaction dynamics.

We are looking for something analogous to symmetry breaking:

```math
\text{initially exchangeable agents}
\rightarrow
\text{small stochastic/history differences}
\rightarrow
\text{feedback amplification}
\rightarrow
\text{persistent functional asymmetry}.
```

A strong pilot would show that initial behavioral diversity is small, private histories cause diversity to grow, different domains become associated with different agents, those associations become persistent, and shared histories suppress the effect.

## What we are NOT claiming

For the first experiment, avoid claims such as:

- “LLM societies undergo a phase transition.”
- “We have proven emergence.”
- “LLMs spontaneously invent social roles in general.”
- “HSE is a complete measure of collective intelligence.”
- “Any multi-agent system becomes better when agents differentiate.”

Safer framing:

> **Pilot study of symmetry breaking and emergent functional differentiation in a controlled LLM society.**

---

# 4. Synthetic micro-worlds

## Why synthetic?

A benchmark such as MMLU creates several confounds:

- the base model already knows most domains;
- “learning” may only change self-description or confidence;
- domains have unequal intrinsic difficulty;
- differences can reflect pretrained knowledge instead of acquired specialization.

For a first controlled experiment, expertise should be **acquired during the run**.

## Proposed task family

Create $K=4$ hidden worlds:

- `ALPHA`
- `BETA`
- `GAMMA`
- `DELTA`

Each world implements a hidden modular rule

```math
f_k(x,y)
=
(a_kx+b_ky+c_k)\bmod 7.
```

Example hidden rules:

```math
f_{\text{ALPHA}}(x,y)
=
(2x+y+1)\bmod 7,
```

```math
f_{\text{BETA}}(x,y)
=
(x+3y+2)\bmod 7,
```

```math
f_{\text{GAMMA}}(x,y)
=
(4x+2y)\bmod 7,
```

```math
f_{\text{DELTA}}(x,y)
=
(3x+5y+4)\bmod 7.
```

The exact coefficients are not scientifically important. What matters is that all worlds have the same structural complexity, their hidden rules are different, the model is not told the coefficients, and agents can infer them from examples and feedback.

Example task:

```text
You are solving a task from World ALPHA.

Input:
x = 3
y = 5

The hidden world follows a fixed rule that you are not given directly.

What is the output?

A) 0
B) 1
C) 2
D) 3
E) 4
F) 5
G) 6
```

Agent output:

```json
{
  "answer": 4,
  "confidence": 0.73
}
```

The environment knows the correct answer exactly.

---

# 5. Agents

Use $N=4$ agents.

Every agent should have:

- the same model and version;
- the same system prompt;
- the same tool access;
- the same decoding configuration;
- the same empty initial memory;
- the same maximum context/memory policy.

The only persistent difference should be an opaque identity:

```text
agent_0
agent_1
agent_2
agent_3
```

Do **not** manually assign roles.

Recommended system prompt:

```text
You are one member of a society solving repeated tasks from several hidden worlds.

All worlds obey stable but initially unknown rules.

Use your private memory of previous tasks and feedback to improve future answers.

For each task return:
1. your predicted answer;
2. a confidence between 0 and 1.

Do not assume that you have a predefined specialty.
Do not invent a social role.
Infer useful regularities only from your own observed experience.
```

---

# 6. Agent memory

Each agent has a private memory

```math
m_i(t).
```

The simplest implementation is a list of past experiences:

```json
{
  "world": "ALPHA",
  "x": 3,
  "y": 5,
  "agent_answer": 4,
  "correct_answer": 5,
  "was_correct": false
}
```

At each new inference, include a bounded summary or recent subset of this memory in the prompt.

For the pilot, avoid sophisticated vector databases or learned memory systems unless already available. A simple deterministic memory representation is scientifically cleaner.

---

# 7. Interaction dynamics

For every round $t$:

1. Sample a world $C_t$.
2. Sample an input $(x_t,y_t)$.
3. Send the same task to all agents.
4. Each agent returns answer and confidence.
5. Select one agent.
6. Score the selected answer.
7. Reveal feedback according to the experimental condition.
8. Update memory.
9. Log everything.

Initial routing rule:

```math
R_t
=
\arg\max_i c_i(q_t),
```

where $c_i$ is the agent's stated confidence.

Ties must be broken randomly.

### Caveat: confidence

LLM confidence is not necessarily calibrated. That is acceptable here because confidence is an **interaction mechanism**, not interpreted as a probability.

Still, log all confidence values.

### Optional exploration

If greedy routing locks in too early, use an $\varepsilon$-greedy selector:

```math
R_t =
\begin{cases}
\text{random agent}, & \text{with probability }\varepsilon,\\
\arg\max_i c_i(q_t), & \text{otherwise}.
\end{cases}
```

Suggested pilot value:

```math
\varepsilon \in [0.05,0.10].
```

Only add this if needed.

---

# 8. Experimental conditions

## A — Shared memory

When an agent is selected and receives feedback, the experience is copied to **all agents**.

Conceptually,

```math
m_1(t)
=
m_2(t)
=
\cdots
=
m_N(t).
```

This suppresses persistent informational asymmetry.

## B — Private memory

Only the selected agent receives feedback.

Therefore,

```math
m_i(t)\neq m_j(t)
```

can emerge.

This allows the positive feedback loop:

```math
\text{experience}
\rightarrow
\text{competence}
\rightarrow
\text{higher confidence}
\rightarrow
\text{more selection}
\rightarrow
\text{more experience}.
```

## Optional C — No memory

Agents never receive persistent feedback. This estimates how much apparent diversity is produced by decoding noise alone.

## Optional D — Explicit specialization

Manually assign one world to each agent. This provides an approximate upper bound for imposed specialization.

---

# 9. Checkpoints and probe evaluations

Suggested horizon:

```math
T=80.
```

Checkpoints:

```math
t\in\{0,20,40,60,80\}.
```

At each checkpoint:

1. freeze agent memories;
2. disable memory updates;
3. evaluate every agent on the exact same fixed probe set;
4. store outputs;
5. compute society-level metrics.

Use $L=40$ probe tasks:

- 10 ALPHA;
- 10 BETA;
- 10 GAMMA;
- 10 DELTA.

The probe set must be generated once and never used for learning.

For each agent,

```math
b_i(t)
=
\left(
s(r_i(t),e_1),
\ldots,
s(r_i(t),e_L)
\right),
```

with binary correctness

```math
s(r_i,e_\ell)
=
\begin{cases}
1, & \text{correct},\\
0, & \text{incorrect}.
\end{cases}
```

Then

```math
B(t)
=
\begin{bmatrix}
b_1(t)^\top\\
\vdots\\
b_N(t)^\top
\end{bmatrix}.
```

---

# 10. Metrics

## 10.1 Hierarchic Social Entropy (HSE)

Behavioral distance:

```math
d_{ij}(t)
=
1-
\frac{
b_i(t)^\top b_j(t)
}{
\|b_i(t)\|_2
\|b_j(t)\|_2
}.
```

If one behavioral vector has zero norm, handle it explicitly. For compatibility with the paper's treatment, a zero-performance actor can be treated as maximally distant from a nonzero actor.

Run single-linkage hierarchical clustering.

For threshold $h$, let $\mathcal C_t(h)$ be the partition. If cluster $c_k$ contains fraction

```math
p_k(h)=\frac{|c_k|}{N},
```

then

```math
H_t(h)
=
-\sum_k p_k(h)\log_2p_k(h).
```

Finally,

```math
\mathrm{HSE}(t)
=
\int H_t(h)\,dh.
```

Because the partition changes only at dendrogram merge distances, compute the integral exactly as a finite sum over intervals.

Useful normalization:

```math
\mathrm{HSE}_{\mathrm{norm}}(t)
=
\frac{\mathrm{HSE}(t)}{\log_2N}.
```

Interpretation:

- low HSE: agents succeed and fail on mostly the same tasks;
- high HSE: agents have different behavioral success profiles.

**High HSE alone does not imply useful specialization.**

---

## 10.2 Task-domain / agent mutual information

Let:

- $C$ = task world;
- $R$ = selected agent.

Estimate

```math
I(C;R)
=
\sum_{c,r}
p(c,r)
\log_2
\frac{p(c,r)}{p(c)p(r)}.
```

This asks:

> Does knowing the task domain tell us which agent will be selected?

At the beginning:

```math
I(C;R)\approx0.
```

If stable specialization emerges:

```math
I(C;R)>0.
```

Normalize with

```math
I_{\mathrm{norm}}(C;R)
=
\frac{I(C;R)}{H(C)}.
```

---

## 10.3 Agent utilization entropy

To detect routing collapse:

```math
H(R)
=
-\sum_i p(R=i)\log_2p(R=i).
```

Normalize:

```math
H_{\mathrm{util}}
=
\frac{H(R)}{\log_2N}.
```

Interpretation:

- $H_{\mathrm{util}}\approx0$: one agent dominates;
- $H_{\mathrm{util}}\approx1$: selections are spread across agents.

---

## 10.4 Complementarity / oracle gain

Individual accuracy:

```math
A_i(t).
```

Best individual:

```math
A_{\mathrm{best}}(t)
=
\max_i A_i(t).
```

Oracle society:

```math
A_{\mathrm{oracle}}(t)
=
\frac1L
\sum_{\ell=1}^{L}
\mathbf 1
\left[
\exists i:
s(r_i(t),e_\ell)=1
\right].
```

Complementarity gain:

```math
\Delta_{\mathrm{comp}}(t)
=
A_{\mathrm{oracle}}(t)
-
A_{\mathrm{best}}(t).
```

This separates behavioral difference from useful complementary competence.

---

## 10.5 Per-domain competence matrix

Construct

```math
A_{ic}(t)
=
P(\text{agent }i\text{ correct}\mid C=c).
```

Visualize as a heatmap.

A diagonal/block structure after a permutation of agent labels is the qualitative signature of specialization.

---

## 10.6 Routing robustness

Generate semantically equivalent variants of routing probes.

For routing policy $\pi_t$,

```math
\rho(t)
=
P\left[
\pi_t(q)
=
\pi_t(\tilde q)
\right].
```

This asks whether emergent specialization is tied to task semantics rather than fragile wording.

---

## 10.7 Temporal role stability

Using a fixed routing probe set:

```math
S_{\mathrm{temporal}}(t)
=
\frac1L
\sum_{\ell=1}^{L}
\mathbf 1
\left[
\pi_t(e_\ell)
=
\pi_{t-\Delta t}(e_\ell)
\right].
```

This is an extension for the dynamical setting, not a metric from the routing paper.

---

# 11. Core hypotheses

### H1 — Behavioral differentiation

```math
\mathrm{HSE}_{\mathrm{private}}(T)
>
\mathrm{HSE}_{\mathrm{shared}}(T).
```

### H2 — Functional specialization

```math
I_{\mathrm{private}}(C;R)
>
I_{\mathrm{shared}}(C;R).
```

### H3 — Complementarity

```math
\Delta_{\mathrm{comp,private}}(T)
>
\Delta_{\mathrm{comp,shared}}(T).
```

### H4 — Persistent roles

```math
S_{\mathrm{temporal}}(t)
```

should increase during later checkpoints if roles consolidate.

### H5 — Shared information suppresses differentiation

Persistent specialization should be weaker when all agents receive identical histories.

---

# 12. Minimum viable experiment

For a same-day pilot:

```text
agents:          4
worlds:          4
interaction:     80 rounds
conditions:      shared vs private
seeds:           3 if possible
checkpoints:     0, 20, 40, 60, 80
probe tasks:     40 total
robustness:      optional small subset
```

If time becomes constrained:

```text
agents:          4
worlds:          4
interaction:     60 rounds
conditions:      shared vs private
seeds:           1
checkpoints:     0, 20, 40, 60
probe tasks:     40
```

One clean seed with complete logging is better than several broken runs.

---

# 13. Suggested repository structure

```text
.
├── EXPERIMENT.md
├── pyproject.toml
├── src/
│   ├── agents.py
│   ├── environment.py
│   ├── router.py
│   ├── memory.py
│   ├── run_experiment.py
│   ├── probes.py
│   └── metrics/
│       ├── hse.py
│       ├── information.py
│       ├── complementarity.py
│       └── robustness.py
├── configs/
│   ├── shared.yaml
│   └── private.yaml
├── data/
│   ├── probe_set.json
│   └── runs/
├── notebooks/
│   └── analysis.ipynb
└── figures/
```

Keep the LLM provider behind one adapter so the experiment is not coupled to a specific API.

---

# 14. Suggested core data structures

```python
@dataclass
class Agent:
    agent_id: str
    memory: list[Experience]
```

```python
@dataclass
class Experience:
    round_id: int
    world: str
    x: int
    y: int
    prediction: int
    confidence: float
    correct_answer: int
    was_correct: bool
```

```python
@dataclass
class AgentResponse:
    agent_id: str
    answer: int
    confidence: float
```

```python
@dataclass
class RoundLog:
    seed: int
    condition: str
    round_id: int
    world: str
    x: int
    y: int
    correct_answer: int
    responses: list[AgentResponse]
    selected_agent: str
    selected_answer: int
    selected_correct: bool
```

---

# 15. Main experiment pseudocode

```python
def run_experiment(config):
    rng = make_rng(config.seed)

    agents = initialize_identical_agents(config)
    environment = HiddenWorldEnvironment(config.worlds)
    probe_set = load_fixed_probe_set()

    evaluate_checkpoint(
        t=0,
        agents=agents,
        probe_set=probe_set,
    )

    for t in range(1, config.num_rounds + 1):
        task = environment.sample_task(rng)

        responses = parallel_map(
            lambda agent: agent.solve(task),
            agents,
        )

        selected = router.select(
            task=task,
            responses=responses,
            rng=rng,
        )

        feedback = environment.evaluate(
            task,
            selected.answer,
        )

        if config.memory_mode == "private":
            agents[selected.agent_id].observe(feedback)

        elif config.memory_mode == "shared":
            for agent in agents:
                agent.observe(feedback)

        log_round(...)

        if t in config.checkpoints:
            evaluate_checkpoint(
                t=t,
                agents=agents,
                probe_set=probe_set,
            )
```

Probe evaluation must never modify agent memory.

---

# 16. HSE implementation sketch

```python
def cosine_behavioral_distance(a, b):
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)

    if na == 0 and nb == 0:
        return 0.0

    if na == 0 or nb == 0:
        return 1.0

    return 1.0 - np.dot(a, b) / (na * nb)
```

Then:

1. compute pairwise distances;
2. run single-linkage clustering;
3. obtain merge heights;
4. for each interval between merge heights:
   - compute partition;
   - compute cluster-size Shannon entropy;
   - multiply entropy by interval width;
5. sum interval contributions.

Unit tests:

### Identical actors

```math
b_1=b_2=\cdots=b_N
\Rightarrow
\mathrm{HSE}=0.
```

### Maximally separated toy actors

For mutually orthogonal profiles over distance range $[0,1]$,

```math
\mathrm{HSE}
\approx
\log_2N.
```

---

# 17. Logging requirements

Save enough information to reconstruct every claim.

For every API call store:

- run ID;
- seed;
- condition;
- round;
- agent ID;
- model;
- model parameters;
- full task;
- relevant memory/context;
- raw model response;
- parsed answer;
- confidence;
- selected agent;
- correct answer;
- feedback recipient(s);
- latency;
- token usage if available.

The raw run is the scientific object.

---

# 18. Reproducibility

At minimum fix and record:

- Python seed;
- task-generator seed;
- tie-breaking seed;
- model name/version;
- temperature;
- top-p;
- max tokens;
- system prompt hash;
- probe-set hash;
- experiment config.

LLM APIs may remain nondeterministic even under fixed seeds. That makes repeated runs more important, not less.

---

# 19. Agent-label permutation problem

Agents begin symmetric.

Across seeds we may see:

```text
seed 1:
ALPHA -> agent_0
BETA  -> agent_2

seed 2:
ALPHA -> agent_3
BETA  -> agent_0
```

These are scientifically equivalent symmetry-broken states.

Do **not** average raw heatmaps across seeds without aligning labels.

Metrics such as HSE, mutual information, utilization entropy, and oracle gain are naturally permutation invariant.

For averaged role visualizations, either show seeds separately or align agents using Hungarian matching.

---

# 20. Primary plots

## Plot 1 — HSE through time

```text
x: interaction round
y: normalized HSE
lines: shared vs private
```

## Plot 2 — $I(C;R)$ through time

```text
x: interaction round
y: normalized mutual information
lines: shared vs private
```

## Plot 3 — Per-domain competence heatmap

Show at $t=0$ and $t=T$.

## Plot 4 — Routing matrix

Rows: worlds.  
Columns: agents.  
Cells:

```math
P(R=i\mid C=c).
```

## Plot 5 — Complementarity gain

```text
x: interaction round
y: oracle accuracy - best individual accuracy
```

## Plot 6 — HSE vs robustness trajectory

```text
x: HSE
y: routing robustness
point color: time
```

This is the cleanest bridge to the routing paper: instead of placing a society at one static point, show its trajectory through the diversity–robustness plane.

---

# 21. Interpretation table

| Observation | Interpretation |
|---|---|
| HSE ↑, MI ↑, complementarity ↑ | Strong evidence of useful functional differentiation |
| HSE ↑, MI ≈ 0 | Agents diverged, but not according to task structure |
| HSE ↑, complementarity ≈ 0 | Different behavior, little useful coverage gain |
| MI ↑, utilization entropy ↓ | Possible monopoly / collapsed routing |
| MI ↑, temporal stability ↑ | Persistent role formation |
| HSE low in shared, high in private | Evidence that asymmetric histories drive differentiation |
| Robustness low | Routing may depend on wording rather than stable specialization |
| All metrics remain low | No specialization under the current dynamics |

A null result is still informative.

---

# 22. Important confounds

## Confidence-induced lock-in

One agent may become overconfident and receive almost every task.

Monitor $H(R)$. If routing collapses, add small exploration.

## Memory length

If one agent receives more tasks, it also receives a longer prompt. Use a fixed-size memory budget or fixed number of retrieved experiences.

## Domain leakage

World labels must be semantically meaningless.

## Probe contamination

Never feed probe answers into memory.

## Unequal world difficulty

Use the same functional family for all worlds and inspect $t=0$ performance.

## Agent identity effects

Use opaque IDs, not names/personas.

## Stochastic diversity is not specialization

Random answers can increase behavioral distance. That is why HSE must be paired with $I(C;R)$, temporal persistence, and complementarity.

---

# 23. MVP checklist

## Harness

- [ ] Implement hidden worlds.
- [ ] Implement identical agent wrapper.
- [ ] Implement JSON output parser.
- [ ] Implement parallel calls.
- [ ] Implement private/shared memory.
- [ ] Implement confidence-based router.
- [ ] Write full round logs.

## Probe system

- [ ] Generate fixed probe set.
- [ ] Evaluate all agents in batch.
- [ ] Save $B(t)$.
- [ ] Verify probes do not update memory.

## Metrics

- [ ] Individual accuracy.
- [ ] Per-domain accuracy.
- [ ] HSE.
- [ ] $I(C;R)$.
- [ ] Utilization entropy.
- [ ] Oracle gain.
- [ ] Temporal stability.
- [ ] Robustness if time permits.

## Main runs

- [ ] Shared memory, seed 1.
- [ ] Private memory, seed 1.
- [ ] Inspect behavior before spending more API budget.
- [ ] Run seeds 2 and 3 if dynamics look sensible.

## Figures

- [ ] HSE vs time.
- [ ] MI vs time.
- [ ] Final competence heatmaps.
- [ ] Routing heatmaps.
- [ ] Complementarity vs time.
- [ ] HSE–robustness trajectory.

---

# 24. Fast decision rule after the first run

After one shared/private seed, inspect:

1. task-to-agent routing heatmap;
2. per-domain accuracy heatmap;
3. HSE trajectory;
4. utilization entropy.

If there is **no differentiation at all**, adjust the interaction mechanism before running more seeds.

Potential fixes, in order:

1. increase number of rounds;
2. ensure private memories actually influence prompts;
3. make hidden rules require several examples;
4. add small $\varepsilon$-greedy exploration;
5. reduce memory leakage;
6. inspect confidence collapse.

Do not spend time polishing HSE if the underlying dynamics are not producing signal.

---

# 25. Future extension: control parameter

Introduce a feedback-privacy parameter

```math
p_{\mathrm{private}}\in[0,1].
```

For each selected experience:

- with probability $p_{\mathrm{private}}$, feedback remains private;
- otherwise it is broadcast.

Sweep:

```math
p_{\mathrm{private}}
\in
\{0,0.25,0.5,0.75,1\}.
```

Measure final HSE, $I(C;R)$, and complementarity.

This creates a first crude “phase-diagram style” experiment.

Call any sharp change a **regime change** until proper finite-size analysis exists.

---

# 26. Future extension: population size

Repeat for

```math
N\in\{2,4,8,16\}.
```

Questions:

- Does larger $N$ increase accessible behavioral diversity?
- Is there a minimum population size for stable division of labor?
- Does excessive population dilute experience per agent?
- Does complementarity saturate?

This is where the connection to statistical physics becomes more serious.

---

# 27. Future extension: communication topology

Put agents on a graph:

- complete graph;
- ring;
- random graph;
- modular graph;
- scale-free graph.

Allow feedback/messages to propagate only through edges.

Potential question:

> How does communication topology affect symmetry breaking, specialization, and collective competence?

---

# 28. Future extension: information-theoretic emergence

The pilot uses

```math
I(C;R)
```

as a simple measure of division of labor.

A deeper project could investigate:

- redundancy;
- unique information;
- synergistic information;
- Partial Information Decomposition;
- O-information;
- information flow through agent interaction graphs.

That moves from:

> “agents became different”

toward:

> “the collective possesses task-relevant information that cannot be assigned to any individual component alone.”

---

# 29. Routing as endogenous differentiation

The most interesting conceptual possibility is the feedback loop

```math
\text{routing}
\rightarrow
\text{asymmetric experience}
\rightarrow
\text{behavioral diversity}
\rightarrow
\text{better routing signal}
\rightarrow
\text{stronger specialization}.
```

The routing paper largely treats actor diversity as something the router encounters.

This experiment asks whether routing itself can become a **generator of the diversity it later exploits**.

---

# 30. Presentation narrative

### 1. Paper question

> When is routing meaningful?

The paper argues that routing should not be judged only by accuracy/cost; the society should also contain behaviorally distinct actors and routing should be robust.

### 2. Our inversion

> What if the actors are not distinct initially?

Start with identical LLM agents and ask whether interaction itself can create the diversity that HSE measures.

### 3. Physical analogy

```math
\text{symmetry}
\rightarrow
\text{fluctuation}
\rightarrow
\text{feedback}
\rightarrow
\text{symmetry breaking}.
```

Use this as motivation, not as proof of a phase transition.

### 4. Experimental system

Four agents. Four hidden worlds. Same model. Same prompt. Private vs shared experience.

### 5. Metrics

- HSE: did agents become behaviorally different?
- $I(C;R)$: did differences organize into division of labor?
- $H(R)$: did routing collapse?
- oracle gain: are differences useful?
- robustness: are roles semantically stable?

### 6. Results

Show trajectories and heatmaps.

### 7. Interpretation

Possible headline:

> **Static routing diversity may itself be an emergent dynamical variable.**

More cautiously:

> **Asymmetric interaction histories can generate the behavioral heterogeneity that static routing metrics later observe.**

---

# 31. Scientific standard for the pilot

A successful pilot requires:

1. a clear mechanism;
2. reproducible logs;
3. a control;
4. one interpretable effect;
5. no exaggerated causal or phase-transition claims.

Examples of informative outcomes:

> “Private memory increased HSE but not task-agent mutual information.”

Agents differentiated without developing functional specialization.

Or:

> “Task-agent MI increased, but oracle gain did not.”

Role assignment emerged without genuine complementary competence.

These are more informative than simply saying “multi-agent was better.”

---

# 32. Core conceptual model

```math
\boxed{
\text{identical agents}
+
\text{stochastic routing}
+
\text{private experience}
+
\text{feedback}
\rightarrow
\text{possible symmetry breaking}
}
```

Measurement:

```math
\boxed{
B(t)
\rightarrow
\mathrm{HSE}(t)
}
```

```math
\boxed{
(C_t,R_t)
\rightarrow
I(C;R)
}
```

```math
\boxed{
\text{probe success sets}
\rightarrow
\Delta_{\mathrm{comp}}
}
```

```math
\boxed{
q,\tilde q
\rightarrow
\rho
}
```

The key distinction is:

> **Diversity tells us that agents differ.  
> Mutual information tells us that the difference is organized.  
> Complementarity tells us that the organization is useful.  
> Robustness tells us that the routing structure is stable.**

---

# 33. Immediate next step

Implement the smallest possible end-to-end loop:

```text
4 identical agents
        ↓
one hidden-world task
        ↓
4 answer + confidence responses
        ↓
select one agent
        ↓
give feedback according to condition
        ↓
update memory
        ↓
repeat
```

Before implementing every metric, run 10–20 rounds and inspect manually whether memories, confidence patterns, and domain-to-agent routing are diverging.

Only then scale the run and compute the full analysis.

---

# 34. Reference paper

Primary conceptual reference:

> *When is Routing Meaningful? Diversity and Robustness in Language Model Societies* — Huot, Kaisers, Lapata (2026).

This experiment is **not** a reproduction of the paper.

It is a dynamical extension inspired by its behavioral diversity and routing robustness framework.

---

# 35. One-sentence project description

> **A controlled study of whether initially homogeneous LLM agents can spontaneously develop persistent, useful specialization through asymmetric interaction histories, measured as a dynamical extension of behavioral diversity metrics used in LLM routing.**
