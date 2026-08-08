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
