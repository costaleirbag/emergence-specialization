# Observable Ecology Learner Calibration V2

**Status: frozen single-agent qualification protocol; no society experiment is authorized by this document.**

## Purpose

V3.1 established an observable semantic ecology whose predictive information `J_obs` and Bayes decision opportunity `L*_obs` are known before model inference. V1 did not provide a clean learner measurement: its static output instruction contained the concrete vector `[0,1,0]`, and its six probes were not input-balanced. The V1 raw data remain preserved as a harness-confounded legacy record. V2 tests only:

`J_obs, L*_obs -> L^DeepSeek`.

It does not test routing, memory locality, specialization, or an LLM society.

## Frozen protocol

- Provider: DeepSeek Direct (Keychain credential only; no OMP/Bitwarden).
- Model: `deepseek-v4-flash`; thinking: off; one completion per prompt.
- Geometries: `GLOBAL`, `BLOCK`, `DIAGONAL`.
- Families: `ACCESS`, `INCIDENT`, `PROVENANCE`, `RELEASE`.
- Environment seeds: `9201, 9202, 9203, 9204`.
- Natural teacher-correct histories only, exactly `h=8`, using the V1 history generator and order. No teaching-selected histories.
- Eight held-out probes per seed and target. The same symbolic support is reused across geometries and families for a paired seed; it is disjoint from the union of all four source histories.
- Probe input marginals are exactly two occurrences of each value `0..3` in each coordinate. Probe labels are not used to select cases; balance follows from the frozen balanced maps.
- Training templates are used for memories and the frozen evaluation template is used for probes. The model never receives family, geometry, theta, or canonical-factor IDs.
- Static instructions contain no complete concrete three-bit answer vector. Memory contains only rendered semantic cases and resolved decisions; it does not contain predictions, confidence, or reasoning.

## Calls and budget

The immutable task manifest must contain exactly:

```text
baseline:  3 geometries × 4 seeds × 4 targets × 8 probes = 384
transfer:  3 geometries × 4 seeds × 4 sources × 4 targets × 8 probes = 1536
total: 1920 logical completions
```

The new external inference ceiling is **US$0.10**, including technical retries. The freeze command measures all rendered prompts and forecasts from observed DeepSeek semantic-task costs. It refuses to proceed unless the forecast plus a 50% margin is within the ceiling. A per-attempt reservation and append-only journal enforce the same cap during execution. Technical failures may retry at most once; valid scientific wrong answers and schema/domain failures are not retried.

## Exact Bayes precondition

Before any paid call, every task receives exact prompt-level posterior metadata under the V3.1 ecology. Baseline opportunity is `A*=0.125`. The frozen gate requires mean informative `A* >= 0.85` for each geometry (all GLOBAL cells, BLOCK diagonal/within-block cells, and DIAGONAL diagonal cells), and exactly `0.125` for independent cells. If this gate fails, execution is blocked.

## Primary quantities and gates

For each geometry/seed, estimate the complete `4×4` matrix `L^DS_cd = accuracy(target d after natural source-c history) − accuracy(d with empty memory)`. Report per-seed matrices before aggregate means. Define `D` as mean diagonal, `O` as mean off-diagonal, and `Q=D−O`. For BLOCK also report within-block `W`, cross-block `C`, and `B=W−C`. Compare realized matrices to exact frozen `L*_obs` using raw/centered cosine and rank diagnostics. Report component-level and joint exact accuracy, response distribution, semantic OOD, anchoring, zero-information transfer, and family effects.

Qualification is deliberately conservative and fixed before inference:

1. `D >= 0.10` in GLOBAL, BLOCK, and DIAGONAL;
2. GLOBAL `O > 0` and `O/D >= 0.50`;
3. BLOCK `W > 0` and `B >= 0.05`;
4. DIAGONAL `D > 0` and `O/D <= 0.50`;
5. `Q_GLOBAL < Q_BLOCK < Q_DIAGONAL`;
6. at least one raw or centered alignment with exact `L*_obs` is positive.

All six must pass for **LEARNER GEOMETRY QUALIFIED**. Otherwise classify as **PARTIAL** or **NOT QUALIFIED**; if static/probe/backend validity fails, classify **HARNESS FAILURE**. None of these outcomes authorizes a society.

## Statistical unit and limitations

The independent unit is the environment seed (`n=4`); probes are repeated measurements within a seed. One provider completion per prompt leaves provider stochasticity unestimated. Eight held-out cases are a qualification pilot, not publication-scale power. Exact Bayes opportunity is an ecology-prior quantity, not a universal upper bound on a pretrained model. Positive transfer in zero-information cells is reported as learner/prior-induced transfer, not ecological transfer. Context length, semantic analogy, answer priors, and joint three-bit composition remain possible explanations.

## Reproducibility and stopping rules

The manifest, task hashes, prompt hashes, probe audit, model identity, provider fingerprints, token usage, costs, retries, raw responses, and health status are frozen or journaled. If the manifest, backend identity, hard budget, or logical coverage is violated, stop and preserve artifacts. After the 1,920 logical calls, stop all external inference. Do not tune prompts, add seeds, change `h`, enable thinking, add teaching, or run a society. The next step is principal researcher review of the learner-response report.
