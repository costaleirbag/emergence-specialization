# Minimal Developmental Society V1 — execution log

## 2026-08-11 missing-usage interruption and resume

The frozen campaign stopped safely after 29,188 terminal logical completions
because one DeepSeek Direct response omitted provider usage data. The pre-patch
runner released its reservation and raised before journaling that physical
attempt. No scientific observation was admitted for the affected logical ID.

- Affected logical ID: `5dbf7ff76cb817536e8d45946a1ea73acdd14a82e17aadac3a21a2584459252d`
- Frozen cell: seed `27102`, regime `RP`, online round `81`, niche `RELEASE`
- Terminal duplicates before repair: `0`
- Observed terminal completions before repair: `29188 / 47104`
- Exact observed cost before repair: `US$0.665364728`

Technical commit `f2ae2fd` changes only retry/accounting infrastructure:

1. every provider attempt is journaled before retry decisions;
2. a missing-usage attempt is nonterminal and never used scientifically;
3. it is charged a conservative `US$0.0005` upper bound;
4. attempt counts persist across resume, preserving the frozen maximum of two
   physical attempts per logical completion;
5. prompts, model, thinking mode, task stream, routing, memory, checkpoints,
   seeds, and scientific metrics are unchanged.

The retroactive accounting event was appended once, bringing the physical
attempt count to 29,189 while terminal coverage remained 29,188. The campaign
ledger and event sum both became `US$0.665864728`, reserved cost remained zero,
and the same logical ID was eligible only for attempt `1` on resume.

Offline validation before resume:

- targeted society tests: 9 passed;
- full suite: 235 passed;
- `compileall`: passed;
- terminal duplicate logical IDs: 0;
- event cost equals budget ledger: yes;
- model identity among recorded terminal attempts: only
  `deepseek-v4-flash`.

This is an infrastructure recovery, not a scientific protocol amendment.
