# Developmental dynamics v2 preflight

Status: **READY FOR THE NEW CLEAN 2×2 CAMPAIGN**

This document records the offline gate before any v2 model call. The legacy v1
artifacts are exploratory and are not reused by the v2 runner.

## Protocol identity

- Campaign: `developmental-dynamics-v2`
- Protocol: `staged-v3-response-semantics`
- Provider: DeepSeek Direct (`deepseek-v4-flash`), Keychain credential source
- Conditions: confidence/private, confidence/shared, random/private, random/shared
- Seeds: 1–10 in every cell (40 runs)
- Agents/rounds: 4 / 20
- Checkpoints: `[0, 10, 20]`
- Fixed probes: 40 per checkpoint
- Nominal completions: 560 per run, 22,400 total
- Physical ceiling: 700 per run, 28,000 total
- Budget guard: USD 2.00 observed campaign cost
- Run parallelism: 1
- Probe hash: `cb234422389ff7d5a04566112a483f147e4a3d1212b1c69fbb0396ec9ca4c55e`

The frozen manifest is
`data/campaigns/developmental-dynamics-v2/campaign.json`.

## Frozen provenance

- Code/config freeze commit: `93d833fa226827274af06a9d6f292e7c51800e02`
- Manifest commit / current HEAD: `1c426a887d0362f70aadbe281771ecd84644caf4`
- Gamma source rule: `HIDDEN_RULES["GAMMA"] == (4, 2, 0)`, so
  `f(x,y) = (4x + 2y) mod 7`. The previous `+3` in a research note was a
  documentation error; code is the source of truth.

Config SHA-256 values:

| Cell | Config | SHA-256 |
|---|---|---|
| confidence/private | `configs/research/v2/clean_confidence_private_20.yaml` | `03c63facce5efb0cad377e9da6f0c5b6b647fe28b296f56c577cb402a133e2a2` |
| confidence/shared | `configs/research/v2/clean_confidence_shared_20.yaml` | `4f388243a2f4a7e048ccac0de49658c9b28c2941078d6be4f8d8db68ff2d3555` |
| random/private | `configs/research/v2/clean_random_private_20.yaml` | `6f83b041e4f32fa10ea6749f1ba6818e24d6cdbe2da09de8d9df660411930a4c` |
| random/shared | `configs/research/v2/clean_random_shared_20.yaml` | `6bb512762a7990269265921ead6d507832472e3c5f8b64b3dfabac9a55da217c` |

## Semantic correction

The parser now distinguishes syntax/schema failure from scientific domain
failure. A JSON response with integer `answer=7` and valid confidence is logged
as `error=null`, `answer_in_domain=false`, and
`semantic_violation=answer_out_of_domain`; it is not retried, remains eligible
for routing, and is scored incorrect by the environment. Malformed output,
invalid confidence, transport errors, and provider errors remain retryable under
the configured technical retry policy.

All previous runs remain immutable legacy/exploratory artifacts. The v2 runner
only scans `data/runs/campaigns/developmental-dynamics-v2` and requires exact
protocol, seed, condition, router, and config identity.

## Offline gates passed

- Unit suite: **117 tests passed**.
- Compile check: `uv run python -m compileall -q src` passed.
- Four config files load successfully.
- Every v2 config uses `deepseek_direct`, `deepseek-v4-flash`, thinking off,
  `recent_k=8`, checkpoints `[0,10,20]`, and the fixed probe hash above.
- Paired task sequences are condition-independent for the 20 rounds.
- Random-routing private/shared sequences are identical under the paired RNG.
- `RandomRouter` is already covered by order-invariance and seeded-RNG tests.
- Keychain status: configured (`keyring.backends.macOS`); no key value was
  printed or accessed by this audit.
- Legacy v1 campaign was not resumed or reused.

## Forecast

Observed completed real runs give approximately USD 0.00002993 per logical
completion. The nominal v2 forecast is approximately **USD 0.670414**, below the
USD 2.00 hard cap. The runner refreshes cost and physical-attempt counters from
raw artifacts before each run and stops safely at either guard.

## Official execution command

The only command authorized for the new campaign is:

```bash
UV_CACHE_DIR=/tmp/uv-cache-es uv run python -m emergent_specialization.clean_campaign --run --confirm-real
```

It executes one v2 run at a time, preserves completed artifacts, and stops on
an incomplete/invalid run or a budget/physical-attempt guard. It never invokes
OMP or Bitwarden. Do not run the legacy `campaign` runner or resume any v1 run.
