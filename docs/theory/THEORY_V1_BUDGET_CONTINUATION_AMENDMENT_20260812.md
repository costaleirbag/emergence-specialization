# Theory V1 budget continuation amendment — 2026-08-12

## Principal-researcher authorization

The hard Theory V1 expenditure ceiling is amended from **US$8.00** to
**US$11.00**. No scientific parameter, prediction, task, prompt, seed, metric,
or stopping criterion is changed.

## Observed-cost forecast at the amendment

| component | USD |
|---|---:|
| completed MICRO | 0.7598045784 |
| quarantined serial MACRO | 0.1230654880 |
| restarted MACRO already observed | 1.8660546072 |
| projected remaining restarted MACRO at current mean cost | 6.6427033308 |
| projected total | 9.3916280044 |
| projected total with 10% remaining-cost margin | 10.0558983374 |

The observed mean restarted-MACRO attempt cost was US$0.0000456549 over 40,873
physical attempts. The margin-adjusted forecast remains below US$11.00.

## Technical accounting repair

The previous hard-budget stop was caused by reservations occurring before a
coroutine entered the global request semaphore. Queued checkpoint coroutines
were thereby counted as billable in-flight requests, leaving US$4.944 in stale
reservations after shutdown. The reservation now occurs only after a request has
acquired one of the 32 global transport slots; stale reservations were released
after confirming the process had stopped.

This is accounting/orchestration only. It neither changes a logical completion
nor accepts/rejects a scientific response differently. The restarted canonical
MACRO journal is resumed rather than rerolled; its state is reconstructed from
its own persisted online-step events.
