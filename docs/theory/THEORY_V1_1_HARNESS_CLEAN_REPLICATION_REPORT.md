# Theory V1.1 harness-clean replication

## Status

**PARTIAL / BLOCKED BEFORE MACRO.** The clean harness validation and fresh MICRO
parameterization completed. The targeted MACRO was not started because the
post-MICRO cost forecast exceeded the frozen US$4.00 ceiling once the required
operational safety margin was applied. No MACRO scientific outcome exists for
Theory V1.1.

## Why Theory V1 required a harness-clean replication

The historical Theory V1 instrument placed a concrete valid answer vector in a
static JSON example. The historical raw responses concentrated on that vector,
so the old prospective challenge remains **prospective but harness-confounded**.
Theory V1.1 changed only the output schema wording: it requests a key named
`decisions` containing exactly three binary integers, without displaying any
complete answer vector. The Theory V1 equations, social state, prompts, model,
thinking mode, seeds within each stage, and scientific retry semantics were not
changed.

## Stage A — harness validation

The frozen Stage A contained 1,024 logical calls across both ecologies and eight
fresh ecology-seed units. It completed with 1,025 physical attempts, one
technical transport retry, one semantic out-of-domain observation, zero parse
failures, and observed cost US$0.0355964336. All gates passed:

| quantity | pooled value |
|---|---:|
| A0 | 0.1015625 |
| A_same(4) | 0.2109375 |
| A_same(8) | 0.2109375 |
| A_foreign(8) | 0.16015625 |
| G_abs(8) | 0.109375 |
| G_rel(8) | 0.1168807695 |
| `[0,1,0]` frequency | 0.1133919844 |
| modal-vector frequency | 0.1886608016 |

HV1–HV5 are all `PASS`. These are instrument gates only; they are not evidence
for Theory V1's social mechanism.

## MICRO — clean parameterization

The fresh MICRO stage completed all 19,584 logical calls (19,588 physical
attempts; four technical parse retries; six semantic out-of-domain observations)
at observed cost US$1.1331386304. Every terminal event uses
`deepseek-v4-flash`; maximum observed request overlap reached the configured 32.
The explicit and pairwise K estimators agreed to a maximum absolute difference of
`1.11e-16`. The primary K artifact is pooled over the six fresh seeds per
ecology and k.

The double-swap diagnostic was deliberately not a go/no-go filter. Its means are
reported descriptively in `reports/theory-v1-1/micro/linearity_diagnostics.csv`.
Across the six seeds, mean R² was negative in every ecology/k panel, while cosine
alignment was positive but imperfect. This is a microscopic assumption
diagnostic, not a reason to alter the frozen equations or add a nonlinear model.

## Sealed predictions

The 16 population prediction rows (eight cells per ecology, k=8) were generated
offline from the pooled fresh MICRO K and sealed before any MACRO call under
`theory-v1-1-predictions-sealed-20260813`. They are not fitted to MACRO data.
The artifact is [prediction_manifest.json](/Users/costaleirbag/dev/emergence-specialization/reports/theory-v1-1/predictions/prediction_manifest.json).

For reference, the frozen predicted excess-growth ordering is monotone in beta
for the private cells in both ecologies; the matched-gain C2/C5 rows are equal by
construction of the Theory V1 effective gain. Sharing rows predict negative
excess growth relative to private beta=0 under the frozen retention equation.

## MACRO cost gate

The fresh MICRO cost was used for the post-MICRO reforecast. The targeted MACRO
manifest is technically frozen at 62,976 logical calls (two ecologies, six fresh
seeds each, eight cells), but no calls were made. The preflight estimates:

| quantity | value |
|---|---:|
| projected MACRO cost | US$2.7389706913 |
| projected total (Stage A + MICRO + MACRO) | US$3.8721093217 |
| projected total with 30% remaining safety margin | US$4.6938005292 |
| hard ceiling | US$4.00 |

The frozen stop rule therefore blocked MACRO. This is a budget/infrastructure
decision, not a scientific result and not an adaptation to MICRO values.

## Theory V1.1 questions

V11-A adaptive ordering, V11-B matched-gain law, V11-C sharing law, and V11-D
adaptive amplification are **not evaluated** because they require MACRO growth
observations. They must not be labeled pass, fail, or inconclusive from the
MICRO K or prediction table alone.

## What changed and what did not

Changed: the concrete-answer output anchor was removed; fresh V1.1 seeds and
separate artifact namespaces were used; the targeted eight-cell manifest and
prediction seal were created.

Unchanged: Theory V1 equations and thresholds; ecological generators; task
semantics; router and memory equations; model/backend (`DeepSeek Direct`,
`deepseek-v4-flash`, thinking off); and the interpretation that a clean MACRO
would be required to test social mechanism claims.

## Epistemic conclusion

The clean instrument passed its validation gate and produced a technically valid
fresh MICRO parameterization. The evidence is insufficient to decide whether the
historical Theory V1 failures were harness artifacts or genuine mechanistic
failures, because the discriminating MACRO was correctly not run under the hard
budget guard. Theory V1.1 is therefore **PARTIAL/BLOCKED**, not supported and not
refuted by this session.

No Theory V2 was defined, no society was run, and no additional inference is
authorized automatically. The next action is principal-researcher review of the
budget decision and whether a future MACRO allocation is justified.

## Provenance

- Branch: `research/developmental-dynamics`
- Prediction seal: `theory-v1-1-predictions-sealed-20260813`
- Stage A raw: `data/auto-research/theory-v1-1/stage_a_events.jsonl`
- MICRO raw: `data/auto-research/theory-v1-1/micro_events.jsonl`
- Stage A cost: US$0.0355964336
- MICRO cost: US$1.1331386304
- Total new inference: US$1.1687350640
- New MACRO calls: `0`
- New external calls after MICRO: `0`
- Stage A raw SHA-256: `d91d5c95c9d7afe5bcd9707fa6a4a1822f3c713f128549d9edaadee4dcaf9bd5`
- MICRO raw SHA-256: `91bf71db05358948a5e6e40dd8eee8f67722b8d0e3633b009315e3adfc28887d`
- MICRO manifest SHA-256: `de847f3089f22da61eaf486d6d3a8f3d5d5fc523d47bc6ce1b446504397b5895`
- Prediction manifest SHA-256: `ee88d43e3e47e11bf068510e37411832c95010a3012b9b9a491981e839062adb`
- Credentials were used only by the authorized DeepSeek Direct stages; no key was
  exposed.
