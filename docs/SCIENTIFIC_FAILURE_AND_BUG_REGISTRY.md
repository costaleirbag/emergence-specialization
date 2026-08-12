# Scientific failure and bug registry

Negative results and implementation failures are part of the provenance record.
The entries below are compact pointers to the detailed reports.

| Issue | Symptom / consequence | Resolution and lesson |
|---|---|---|
| OMP/Bitwarden process coupling | Real smoke required wrapper authentication and fresh OMP processes | Secure launcher and later Direct Keychain path; never expose credentials |
| OMP latency / retries | Probe calls were slow and occasionally recovered | Health must separate logical completions, attempts, retries, and usage |
| Structured-response parser fragility | Prose/braces caused avoidable parse retries | Balanced-candidate parser and regression tests |
| Missing usage fields | Some provider events lacked input/output usage | Report partial/unavailable usage; never invent token cost |
| Learner prompt/harness confounds | Early calibration could not cleanly identify ecological transfer | Harness-corrected V2 and explicit zero-information controls |
| GF(7) same-operation ecology | Coefficient variation may not instantiate distinct functional roles | Retain as mechanistic/null ecology; qualify local plasticity separately |
| Observable ecology qualification limits | Learner geometry remained partial | Do not run a society from a partial microscopic gate |
| Cross-domain transfer bottleneck | Full geometry gate was not identifiable in the frozen ladder | Report partial diagnostic; no post-hoc completion |
| Minimal society competence accumulator | Accuracy exceeded one in derived competence tables | Preserve invalid outputs, repair from raw events, record hashes |
| Verdict bookkeeping residue | Scalar functional-organization field disagreed with repaired three-layer verdict | Canonicalize to `PARTIAL`, preserve old value under `legacy_fields` |
| Team-utility window bookkeeping | `last32_team_utility` summary included non-final segments | Filter explicitly on `segment == last32`; raw online events unchanged |

The registry does not convert a failure into a null result or delete the
artifact that exposed it. Each entry must be read with its phase report before
being cited.
