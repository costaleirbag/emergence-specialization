# Minimal developmental society formalism

For N=K=4, each host agent has a bounded controlled memory M_i(t) and a held-out competence matrix A(t). The router keeps a host-side Beta–Bernoulli estimate μ_ic=α_ic/(α_ic+β_ic), initialized at 1/8. Adaptive allocation is p_i(c,t)=(1−ε)softmax_i[β μ_ic]+ε/N; RP is uniform. Selected-agent feedback is private in RP/AP4/AP12 and copied to every agent in AS12.

Let P_N=I−11ᵀ/N and P_K=I−11ᵀ/K. The finite-system specialization statistic is Ψ_spec(A)=||P_N A P_K||²_F/(NK). It removes agent main effects and niche main effects, retaining the agent×niche interaction. Φ(A)=mean_c Var_i(A_ic) is total differentiation, not specialization. Matching gain compares a one-to-one assignment with the best single generalist.

A positive Ψ is an operational trajectory-level asymmetry measure, not a thermodynamic phase transition and not by itself evidence of roles, causality, or useful division of labor.
