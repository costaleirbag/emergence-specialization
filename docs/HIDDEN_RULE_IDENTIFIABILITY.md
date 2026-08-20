# Hidden-rule identifiability over GF(7)

**Status:** exact offline audit and symbolic positive control. No model call.

Each world has

$$
z=ax+by+c\pmod 7.
$$

For observed examples, define the design matrix over the finite field GF(7):

$$
M=
\begin{bmatrix}
x_1\bmod7 & y_1\bmod7 & 1\\
\vdots & \vdots & \vdots\\
x_k\bmod7 & y_k\bmod7 & 1
\end{bmatrix}.
$$

The coefficient triple is uniquely identifiable exactly when the labels are
consistent and `rank_GF(7)(M)=3`. Three observations are the minimum in
principle, but their residue points must be non-collinear. For a consistent
rank-`r` system, the exact number of candidate rules is `7^(3-r)`.

Consequences:

- `k=1` and `k=2` can never identify three coefficients;
- integer inputs differing by multiples of seven are the same design point;
- rank three with extra contradictory labels is inconsistent, not uniquely
  solvable;
- a systematic `+1 mod 7` label shift is itself a coherent wrong rule with
  coefficients `(a,b,c+1)`.

## Exact audit of executed calibration contexts

The read-only auditor inspected every physical context present in both
calibration JSONLs, including unsuccessful thinking-on attempts. Target-world
rank used only examples from the target world; unrelated rows were not pooled.

### memory-learnability-v1

| Condition | k | Contexts | Rank distribution | Full rank |
|---|---:|---:|---|---:|
| same world | 0 | 40 | r0: 40 | 0/40 |
| same world | 1 | 40 | r1: 40 | 0/40 |
| same world | 2 | 40 | r1: 2, r2: 38 | 0/40 |
| same world | 4 | 40 | r3: 40 | 40/40 |
| same world | 8 | 40 | r3: 40 | 40/40 |
| wrong prediction + correct feedback | 8 | 40 | r3: 40 | 40/40 |
| unrelated world | 8 | 40 | r0: 40 | 0/40 |
| mixed, two target examples | 8 | 40 | r1: 2, r2: 38 | 0/40 |

All 1,560 distinct visible `correct_answer` labels match the hidden environment.
The old “corrupted” arm has wrong prior predictions but truthful feedback; a
solver using feedback recovers the true rule in all 40 full-rank contexts.

### memory-representation-thinking-v1

For thinking-off correct feedback, each nonzero row below applies independently
to full-experience and feedback-only renderings (40 contexts each).

| k | Rank distribution per representation | Full rank |
|---:|---|---:|
| 0 common | r0: 40 | 0/40 |
| 1 | r1: 40 | 0/40 |
| 2 | r1: 2, r2: 38 | 0/40 |
| 4 | r2: 1, r3: 39 | 39/40 |
| 8 | r3: 40 | 40/40 |

All 40 truly-corrupted feedback-only `k=8` contexts are rank three. Their
visible labels are shifted by one, so exact symbolic recovery returns a unique
wrong intercept. That control tests response to coherent false feedback, not
random label noise.

The raw file also contains nine attempted high-thinking ALPHA/seed-1 contexts;
they are kept as distinct reasoning-mode contexts. The overall audit contains
729 attempted contexts: 320 from the first calibration and 409 from the second,
of which 406 second-calibration contexts have at least one successful response.

## Symbolic positive control

The exact solver recovers the environment rule in **100% of truthful, rank-full
contexts** and obtains **1.0 probe accuracy** from those recovered rules. This
validates the exemplar generator, hidden-world labels, probe labels, modular
algebra, and the mathematical learnability of the task.

It does not validate LLM induction. On the contrary, because almost every `k=4`
and every `k=8` truthful context is identifiable, the weak thinking-off learning
curves at those sizes cannot generally be explained by insufficient rank.

## Modular holdout leakage

The calibration excluded exact `(x,y)` overlap but initially failed to exclude
equivalent residue classes `(x mod 7,y mod 7)`. For same-world contexts, the
fraction of responses whose probe had a congruent exemplar was:

| k | Alias fraction |
|---:|---:|
| 1 | 1.8% |
| 2 | 3.3% |
| 4 | 8.0% |
| 8 | 16.3% |

At `k=8`, accuracy was about 0.462 on alias responses and 0.128 on genuinely
non-alias responses. In the balanced thinking-off calibration, the alias rate
was 12.9% at `k=8`; correct-feedback accuracy was about 0.238--0.239 on aliases
and 0.122--0.124 off aliases, depending on representation.

Thus prior “held-out” accuracy partly measures residue-case reuse. The corrected
scientific statement is narrower and stronger: reliable rule induction was not
demonstrated even though `k=4/8` contexts were usually identifiable, and the
truly non-alias performance was weaker than the headline average.

## Reproduction

```bash
PYTHONPATH=src .venv/bin/python -m emergent_specialization.hidden_rule_identifiability
```

Outputs:

- `reports/auto-research/identifiability/context_identifiability.csv`
- `reports/auto-research/identifiability/identifiability_summary.json`

