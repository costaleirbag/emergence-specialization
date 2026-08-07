"""Small, dependency-free aggregation over completed run directories."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

from .analysis import CHECKPOINT_SCALARS, RunBundle, checkpoint_rows, load_run, overview_record


def _summary(values: Sequence[float]) -> dict[str, float | int | None]:
    if not values:
        return {"n": 0, "mean": None, "median": None, "std": None}
    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "std": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


def aggregate_runs(run_dirs: Iterable[str | Path]) -> dict[str, Any]:
    """Return per-checkpoint summaries and paired condition differences.

    Agent labels never enter the scalar aggregation. Matrix alignment is kept
    in :mod:`metrics.permutation` so callers must request that operation
    explicitly rather than accidentally averaging arbitrary labels.
    """
    bundles = [load_run(path) for path in run_dirs]
    scalar_values: dict[tuple[str, int, str], list[float]] = defaultdict(list)
    for bundle in bundles:
        for row in checkpoint_rows(bundle):
            condition = str(row["condition"])
            checkpoint = int(row["checkpoint"])
            for metric in CHECKPOINT_SCALARS:
                value = row.get(metric)
                if isinstance(value, (int, float)):
                    scalar_values[(condition, checkpoint, metric)].append(float(value))
    checkpoint_summary: list[dict[str, Any]] = []
    for (condition, checkpoint, metric), values in sorted(scalar_values.items()):
        checkpoint_summary.append(
            {"condition": condition, "checkpoint": checkpoint, "metric": metric, **_summary(values)}
        )

    by_seed_condition: dict[tuple[int | None, str], RunBundle] = {
        (bundle.seed, bundle.condition): bundle for bundle in bundles
    }
    conditions = sorted({bundle.condition for bundle in bundles})
    paired_differences: list[dict[str, Any]] = []
    paired_delta_hse: list[dict[str, Any]] = []
    if len(conditions) >= 2:
        left, right = conditions[:2]
        seeds = sorted({bundle.seed for bundle in bundles if bundle.seed is not None})
        for seed in seeds:
            left_bundle = by_seed_condition.get((seed, left))
            right_bundle = by_seed_condition.get((seed, right))
            if left_bundle is None or right_bundle is None:
                continue
            left_rows = {int(row["checkpoint"]): row for row in checkpoint_rows(left_bundle)}
            right_rows = {int(row["checkpoint"]): row for row in checkpoint_rows(right_bundle)}
            left_baseline = left_rows.get(0, {}).get("normalized_hse")
            right_baseline = right_rows.get(0, {}).get("normalized_hse")
            for checkpoint in sorted(set(left_rows) & set(right_rows)):
                for metric in CHECKPOINT_SCALARS:
                    left_value = left_rows[checkpoint].get(metric)
                    right_value = right_rows[checkpoint].get(metric)
                    if isinstance(left_value, (int, float)) and isinstance(right_value, (int, float)):
                        paired_differences.append(
                            {
                                "seed": seed,
                                "checkpoint": checkpoint,
                                "metric": metric,
                                "left_condition": left,
                                "right_condition": right,
                                "left_value": left_value,
                                "right_value": right_value,
                                "right_minus_left": float(right_value) - float(left_value),
                            }
                        )
                left_hse = left_rows[checkpoint].get("normalized_hse")
                right_hse = right_rows[checkpoint].get("normalized_hse")
                if all(isinstance(value, (int, float)) for value in (left_hse, right_hse, left_baseline, right_baseline)):
                    left_delta = float(left_hse) - float(left_baseline)
                    right_delta = float(right_hse) - float(right_baseline)
                    paired_delta_hse.append(
                        {
                            "seed": seed,
                            "checkpoint": checkpoint,
                            "left_condition": left,
                            "right_condition": right,
                            "private_or_left_delta_normalized_hse": left_delta,
                            "shared_or_right_delta_normalized_hse": right_delta,
                            "paired_difference_right_minus_left": right_delta - left_delta,
                        }
                    )
    return {
        "schema_version": 1,
        "runs": [overview_record(bundle) for bundle in bundles],
        "conditions": conditions,
        "checkpoint_summary": checkpoint_summary,
        "paired_differences": paired_differences,
        "paired_delta_hse": paired_delta_hse,
    }


def write_aggregate(run_dirs: Iterable[str | Path], output: str | Path) -> Path:
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(aggregate_runs(run_dirs), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Aggregate completed runs offline")
    parser.add_argument("runs", nargs="+", help="Completed run directories")
    parser.add_argument("--output", required=True, help="JSON output path")
    args = parser.parse_args(list(argv) if argv is not None else None)
    destination = write_aggregate(args.runs, args.output)
    print(f"Wrote aggregate analysis: {destination}")


if __name__ == "__main__":
    main()
