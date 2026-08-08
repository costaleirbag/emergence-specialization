# Transfer operator formalism V1

This document defines the mathematical objects used by
TRANSFER-GEOMETRY-CONTROL-V1. Matrices use **SOURCE × TARGET** indexing.

## Ecology and designed geometry

An ecology is

$$E=(C,\Theta,P,V,S),$$

where $C=\{1,\ldots,K\}$ is the set of niche families, $\Theta$ is the
run-specific latent environment, $P_c(x\mid\theta)$ generates tasks, $V_c$
is the exact verifier, and $S\in\{0,1\}^{K\times M}$ is the latent-factor
incidence matrix. Here $K=4$, with canonical OPE families ACCESS, RELEASE,
INCIDENT, and PROVENANCE.

If $s_c$ is row $c$, the designed overlap is

$$G_{cd}=\frac{\langle s_c,s_d\rangle_W}
{\sqrt{\langle s_c,s_c\rangle_W\langle s_d,s_d\rangle_W}},
\qquad G_{cc}=1.$$

Shared factors also share the same run-specific parameter/value. Incidence by
itself is not treated as learned transfer.

## Empirical transfer

Let $A_d^0$ be held-out target accuracy with empty memory and
$A_d^{c,h}$ accuracy after $h$ source-$c$ experiences:

$$L_{cd}(h)=A_d^{c,h}-A_d^0.$$

The primary matrix is $L^{nat}$, from ordinary task sampling. $L^{teach}$
uses the exact greedy predictive-information criterion and is an upper-bound
positive control. Natural and teaching streams are frozen before inference;
the first four experiences nest inside the eight-experience stream.

## Centered operator

$$P_K=I_K-\frac1K\mathbf1\mathbf1^T,\qquad
D_\rho=\operatorname{diag}(\rho),$$

and, for uniform $\rho_c=1/K$,

$$T(L)=P_KL^TD_\rho P_K.$$

The projection removes uniform/generalist improvement and retains niche
contrasts. It is an analysis object, not a universal social Jacobian.

## Effective dynamics and linear stability

For competence $a_i(t)\in\mathbb R^K$, competence-sensitive allocation is

$$p_i(c)=\frac{\exp(\beta a_{ic})}{\sum_j\exp(\beta a_{jc})},
\qquad e_{i,c}=\rho_cp_i(c),$$

with the explicit minimal model

$$\dot a_i=\eta P_KL^Te_i-\gamma a_i.$$

At the exchangeable state, for zero-sum across-agent perturbations,
$\delta p_i(c)=\beta\delta a_{ic}/N$. Restricting competence perturbations
to the contrast subspace gives

$$\dot{\delta a_i}=\left[\frac{\eta\beta}{N}P_KL^TD_\rho P_K-\gamma I\right]\delta a_i,$$

so

$$J_{specialization}=\frac{\eta\beta}{N}T(L)-\gamma I,\qquad
\chi(L)=\max\operatorname{Re}\operatorname{eig}(T(L)).$$

Within this model, a growing contrast mode requires
$\chi(L)>N\gamma/(\eta\beta)$. This is not a theorem about an LLM.

## Analytic limits

For $L=\alpha\mathbf1\mathbf1^T$, $P_KL^TP_K=0$, hence $T=0$ and
$\chi=0$: uniform learning produces no contrast drive. For $L=qI$,
$P_KLP_K=qP_K$, giving $K-1$ degenerate contrast modes with $T$-eigenvalue
$q/K$ under uniform frequency.

For

$$L_{block}=\begin{pmatrix}d&w&c&c\\w&d&c&c\\c&c&d&w\\c&c&w&d\end{pmatrix},
\quad d>w>c,$$

the block mode $(1,1,-1,-1)$ has $L$-eigenvalue $d+w-2c$, while the
within-block modes $(1,-1,0,0)$ and $(0,0,1,-1)$ have eigenvalue $d-w$.
Under uniform frequency, divide these values by $K=4$ for the corresponding
$T$-eigenvalues.

## Descriptors

$$D=\operatorname{mean}_cL_{cc},\quad O=\operatorname{mean}_{c\ne d}L_{cd},\quad Q=D-O,$$

$E_T=\|T\|_F$, $\chi=\max\operatorname{Re}\operatorname{eig}(T)$, and

$$r_{eff}=\frac{(\sum_j\sigma_j)^2}{\sum_j\sigma_j^2},\qquad
A_{dir}=\frac{\|T-T^T\|_F}{\|T+T^T\|_F}.$$

The implementation also reports designed/observed Spearman alignment,
centered Frobenius cosine, spectra, block Rayleigh quotients, theta-specificity,
and teaching-natural gaps.
