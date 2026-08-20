# Autonomous research technical report

## Scope and provenance

- Branch: `research/developmental-dynamics`.
- Session start HEAD: `3db7f54ec93254a570dd1f2e3b43870fdcee1dad`.
- First frozen analysis milestone: `e3577ce`.
- Task-ecology milestone: `67063dc`; non-alias amendment `dff890a`.
- AR-001 implementation: `468a6f2`; frozen probe: `13f40d9`;
  execution authorization/credential-boundary commits: `4e13625`, `96ea83f`.
- AR-001 execution HEAD: `96ea83f4b133225f30e704efd95c81fded8a6fd5`.
- User-owned untracked files and historical raw artifacts were preserved.

The configured `gpt-5.6-luna` worker route was unavailable; bounded fallback
workers used the runtime-advertised model and are recorded in the research log.
Final scientific judgment remained with the parent session.

## Existing-data audits

### Clean v2 society data

The clean 2x2 contains 40 completed runs (private/shared x confidence/random x
10 seeds), 22,400 logical and 22,436 physical calls. The behavioral-HSE contrast
at t=20 was recomputed from all 120 checkpoint competence/behavior matrices.
Native cosine/single linkage reproduced stored HSE to max absolute error
`1.67e-16`.

For native HSE, private minus shared at t=20 was 0.2674 under confidence routing
(8/10 positive seed pairs) and 0.2569 under random routing (9/10). Every tested
distance (`cosine`, binary `hamming`, binary `jaccard`) crossed with
single/complete/average linkage remained positive. In 1,000 paired probe
bootstraps the contrast was positive in every replicate for the two native
router comparisons; every one-of-40 probe deletion remained positive. Probe
bootstrap is a sensitivity analysis, not a replacement for seed-level
replication.

### Prompt exposure and modular aliases

Raw analysis uses logged `memory_inserted`, not reconstructed full history.
Shared recent-k displays eight experiences at t=10/20 with mean age 3.5; private
usually displays about 2.5 at t=10 and 4.7--4.9 at t=20, with much older t=20
items. Thus locality, volume, coverage, and recency jointly differ.

The original calibration excluded exact coordinates but not equality modulo
seven. In old same-world k8, 195/1200 responses were exact target-world modular
aliases. Mean accuracy was about 0.462 on aliases and 0.128 off aliases; unrelated
k8 off-alias accuracy was 0.174. In the newer thinking-off calibration,
same-world k8 off-alias accuracy was about 0.124 (`feedback_only`) and 0.122
(`full_experience`), versus 0.126 at k0. These are nested descriptive means,
not causal estimates of a transfer matrix.

### Exact identifiability

The design matrix for `(a,b,c)` over GF(7) has rows `[x mod 7, y mod 7, 1]`.
Unique recovery requires rank three. k1/k2 cannot identify three coefficients;
almost every k4 and every truthful k8 audited context is rank-full. For 202
truthful full-rank contexts in the representation calibration, exact offline rule
recovery and symbolic probe execution are both 1.0. This proves information
sufficiency, not model induction.

## AR-001 preregistration and implementation review

AR-001 asked whether thinking-off V4 Flash executes a supplied GF(7) rule. Its
frozen config SHA256 is
`462aa3a7ccbdac52be1d34050eb9c497ee0da9a9eab03740996e0080b23e6d90`;
probe hash is
`7c5370122b553dafbd1ef950f3b4de9ca9636f7c3922cb31800169638b59c2df`.
The primary threshold was >=0.85 for reliable execution and <=0.35 for an
execution bottleneck. Valid wrong/OOD answers were never retried.

Three adversarial implementation reviews occurred before inference. Two blocked
unsafe drafts (cost derivation/ledger, credential source, resume identity,
terminal health, provider model, durability, output locking). The final runner
used a demonstrated per-attempt upper bound US$0.00462336, reserved US$0.005,
an observed experiment cap US$0.05, an experiment-scoped ledger, append+fsync
events, atomic manifests, exact model validation, strong logical IDs, one
process lock, and terminal fail-closed states. Fourteen focused and 162 full
tests passed before launch.

The sandboxed first launch could not read Keychain and stopped at 0 attempts,
0 cost. Its terminal manifest was archived separately. A status-only check
outside the sandbox confirmed the expected macOS Keyring without exposing the
secret; the clean launch then ran outside that boundary.

## AR-001 raw result

| Quantity | Value |
|---|---:|
| Unique logical successes | 168 / 168 |
| Physical attempts | 168 |
| Retries / errors / semantic OOD | 0 / 0 / 0 |
| Correct | 153 / 168 (0.910714) |
| ALPHA / BETA / GAMMA / DELTA | 39/42 / 41/42 / 37/42 / 36/42 |
| Exact 3-way answer agreement | 44 / 56 (0.785714) |
| Mean pairwise answer agreement | 0.845238 |
| Input / output / total tokens | 18,060 / 2,030 / 20,090 |
| Usage coverage | 168 / 168 |
| Configured-price cost | US$0.0030968 |
| Mean / median latency | 1.0997 s / 1.1034 s |
| Provider fingerprints | 1 |

Independent validation recomputed these quantities from raw JSONL and exactly
reconciled manifest and ledger. Cost is token usage times frozen prices, not an
independent provider invoice.

### Post-run limitation

All 56 frozen probes have `x=0`, while `y` spans 0--13. The historical balanced
constructor selected the first two coordinate pairs per answer label in
lexicographic order. AR-001 therefore evaluates `z=b*y+c`; it cannot validate
the `a*x` term. This limitation was discovered after completion and is retained
as such. It weakens H7 without closing it.

## Theory and construct validity

The two-mechanism theory separates a competence state from a contextual-anchor
state. The present data can be generated qualitatively by the latter, but no
anchoring-only simulation or causal memory-order intervention was used as proof.

The ecology extension defines

`L_cd(h) = E[post-pre on d | exposure c] - E[post-pre on d | placebo]`.

Useful summaries include diagonal learnability, within-source locality,
directed asymmetry, and negative off-diagonal interference, always reported with
the full matrix. Endogenous routing cannot estimate `L` because exposure is
confounded with prior response/confidence; use matched copies and randomized
forced exposure first.

GF(7) is both empirically hard to induce under this renderer and structurally
narrow for broad roles. These are independent conclusions. It remains a useful
mechanistic/null ecology and may still support narrow coefficient-specific
adaptation if a clean transfer matrix shows it.

## Literature boundary

Primary sources and limitations are recorded in
`docs/LITERATURE_NOTES_AUTO_RESEARCH.md`. Taskonomy motivates directed measured
transfer; gSCAN and CLUTRR motivate generated semantic tasks with exact latent
interpreters; continual-learning work motivates asymmetric transfer and
interference. ROMA/Dean et al. separate behavioral diversity from functional
allocation. The recent EVOCHAMBER preprint overlaps strongly with spontaneous
identical-agent roles, so novelty cannot rest on role emergence alone.

No source proves the current anchoring mechanism, and no novelty claim is
treated as settled.

## Negative results and unresolved problems

- No clean non-alias same-world competence gain was detected.
- Feedback-only representation did not repair accuracy.
- The thinking-on arm remains technically incomplete and incomparable.
- Confidence is not a useful competence signal in current protocols.
- Shared/private memory quantity and age remain treatment components/confounds.
- AR-001 is one-dimensional because of the frozen probe generator.
- The full causal `L_cd(h)` matrix is unmeasured.
- No evidence yet connects behavioral HSE to useful division of labor.

## Stopping decision

No further paid experiment was launched. A new semantic society would skip the
microscopic ecology gate, while a corrected 2D GF(7) execution test would refine
a secondary bottleneck but not solve construct validity. The next milestone is
human review of an offline procedural-ecology specification, followed—only if
its generators/verifiers pass—by a preregistered 48-call transfer screen.

