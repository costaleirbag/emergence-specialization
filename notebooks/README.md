# Generated reports

The report commands generate executed Jupyter notebooks; the notebooks in
`reports/<report-id>/` are derived artifacts, not sources of scientific truth.
All data transformations and plotting functions live in the Python package so
notebook cells remain short, ordered, and reproducible.

Generate a single-run report:

```bash
uv run --group report emergence-report --run data/runs/<run-id>
```

Compare conditions or seeds:

```bash
uv run --group report emergence-compare --runs data/runs/<run-a> data/runs/<run-b>
```
