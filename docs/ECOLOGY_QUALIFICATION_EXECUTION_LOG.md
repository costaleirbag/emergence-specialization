# Ecology qualification execution log

## Start provenance

- Start HEAD: `0aa0c25f8f9109af60411ea280675bfa09694408`
- Branch: `research/developmental-dynamics`
- Existing tracked scientific tests: 162 passed before this phase
- Existing compile check: passed
- Existing new paid diagnostic: AR-001, complete/CLEAN, US$0.0030968
- Existing society experiments: preserved; none will be rerun here
- Backend for this phase: DeepSeek Direct only; OMP and Bitwarden prohibited
- New external inference hard ceiling: US$0.50 including AR-001B and ecology
  qualification retries

## Frozen execution order

1. Implement AR-001B full-2D explicit execution control.
2. Generate and audit OPE and CWDE offline over 100 environment seeds each.
3. Commit implementation, manifests, and tests.
4. Run AR-001B with 112 logical calls.
5. Run only candidates that pass offline gates, with 5 predeclared seeds and
   1,920 logical calls per candidate.
6. Aggregate transfer matrices and stop. No society experiment, tuning, new
   seeds, model, or follow-up is permitted in this phase.

## Scientific freeze

Output classes, generator seeds, template split, latent-state separation,
predictive-identifiability threshold, transfer thresholds, and paid seed list
are fixed by the external protocol. A failed candidate is reported, not
redesigned.

## Implementation freeze

- Implementation commit: `4b3399f`
- Tests after implementation: 165 passed
- Compileall: PASS
- Offline audit: 800 rows; OPE PASS; CWDE PASS
- OPE manifest hash: `c4309b111a27fc5ee9f1f6a570d12db68f7b47fdb51a88baefdb7ea29ea47dc3`
- CWDE manifest hash: `2f8b39e52f81bded2cf779d3d284de6ed85ec8ac981e9135aa5a8cacf5ef5860`
- Both manifests: five fixed environment seeds, 1,920 logical calls each
- AR-001B probe hash: `ac0a8df29f25f1ed5f85f5e48b8ece8cf3947203fd1d27b479b2cd071adb2936`
- Offline generator criteria passed without model calls.

## AR-001B result

- Run directory: `data/auto-research/ar001b-full-2d/`
- Status: completed; all 112 logical completions recovered on the first
  physical attempt; retries: 0; errors: 0
- Model/provider: DeepSeek Direct `deepseek-v4-flash`; all provider records
  reported the expected model
- Full-2D probe coverage: 56/56 probes had nonzero `x` and nonzero `y`
- Exact answer accuracy: `38/112 = 0.3393`
- Usage: 11,088 input tokens, 1,459 output tokens, 12,547 total; usage
  coverage 100%; configured-price estimate: US$0.00196084
- Interpretation gate (pre-registered): accuracy below 0.70 leaves arithmetic
  execution a serious substrate problem. This is a diagnostic limitation, not
  a reason to redesign or retune the candidate ecologies; the frozen protocol
  requires reporting it before transfer qualification.

The result is therefore not evidence that the semantic ecologies will or will
not qualify. It is evidence that the old GF(7) explicit execution control is a
weak positive control for this model under the selected prompt and decoding.
