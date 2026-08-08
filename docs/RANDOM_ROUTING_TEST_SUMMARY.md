# Random-routing control validation

Offline validation after report generation (2026-08-08):

```text
uv run python -m unittest discover -s tests -v
Ran 111 tests in 8.840s
OK

uv run python -m compileall -q src
compileall=OK
```

The report generator reads run artifacts only and does not construct a model
provider. No test or analysis command in this validation made a DeepSeek, OMP,
or external LLM call.
