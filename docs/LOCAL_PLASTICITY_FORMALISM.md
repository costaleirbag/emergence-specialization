# Local Plasticity Curve — Minimal Formalism

Let `a_ic(h)` denote the competence of learner/agent `i` on niche `c` after h
resolved examples from a source history. In this single-agent gate, aggregate
over the repeated probes and write:

```text
f_c(h)       = A_same,c(h)
g_dc(h)      = A_foreign,d→c(h)
G_abs,c(h)   = f_c(h) - f_c(0)
G_rel,c(h)   = f_c(h) - mean_{d != c} g_dc(h)
```

`G_abs` measures useful local learning. `G_rel` measures niche selectivity.
`G_foreign = A_foreign - A0` is reported separately because foreign context can
be helpful, neutral, or harmful. A positive `G_rel` alone is not sufficient if
it is produced only by harming the foreign condition.

The minimal future developmental loop is:

```text
small competence asymmetry
        → competence-sensitive exposure
        → differential local experience
        → differential competence growth
```

For a future society, a minimal allocation model could use
`p(i|c,t) ∝ exp(beta a_ic(t))`, while local experience updates `a_ic(t)`. That
is a future effective hypothesis, not an implemented mechanism here.

The stronger transfer-geometry objects `J`, `L`, `Pi`, and `T(L)` remain a
separate future track. They are not prerequisites for this microscopic gate and
are not reintroduced into its primary analysis.
