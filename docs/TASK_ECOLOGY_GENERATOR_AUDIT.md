# Task ecology generator audit

The authoritative machine-readable audit is
`reports/task-ecology/qualification-v1/offline_generator_audit.csv`.

For each ecology, all four host families and seeds 0--99 were checked for:

- deterministic replay;
- four-class balance (two probes per class);
- exact verifier/oracle correctness;
- no train/probe case overlap or duplicate IDs;
- separate training/evaluation templates and entities;
- no hidden theta key leakage in rendered cases;
- exact candidate-state enumeration;
- predictive identifiability at h=4 and h=8.

The offline gate requires h=8 predictive identifiability >=90% for every family
and seed. Only candidates satisfying every check may receive model calls. The
audit is descriptive qualification, not evidence of model learning or society
specialization.

