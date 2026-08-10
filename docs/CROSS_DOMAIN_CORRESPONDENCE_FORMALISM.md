# Cross-Domain Correspondence Formalism

Let `Pi_cd` denote the host-defined correspondence between source niche `c` and
target niche `d`. It maps the three source attributes to the three target
attributes, their four semantic states, and the three decision components. In
the V3.1 generator this correspondence is an isomorphism through canonical
coordinates `(x1,x2,x3)`; the model-facing semantic renderer does not expose
those coordinates.

Cross-domain learner transfer therefore depends on more than a relation bit:

```text
H_c -> source policy estimate
(R_cd, Pi_cd) -> policy transport
O_d -> target action
```

An intentionally schematic realized transfer map is:

```text
L^m_cd = F_m(H_c, O_d, R_cd, Pi_cd).
```

This is not a claim of literal neural modularity. The exact Bayes oracle has
access to canonical decoding and therefore implicitly possesses `Pi_cd`; a
language-model prompt with relation text does not automatically provide that
same information. A1 supplies `Pi_cd` in semantic language, A2 makes it
trivial through canonical states, and A3/A4 remove source-policy induction as
positive controls.

Eventually a developmental agent may need a belief `q_i(R, Pi, t)` over both
policy coupling and representational alignment. That is a future hypothesis,
not an implemented society state and not an inference from this diagnostic.
