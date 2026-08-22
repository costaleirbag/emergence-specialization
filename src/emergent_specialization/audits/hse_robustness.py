"""Frozen, offline HSE robustness audit for the clean-v2 campaign.

This module only reads the campaign manifest and completed ``metrics.jsonl``
artifacts.  It never instantiates a provider and does not modify raw data.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST = ROOT / "data/campaigns/developmental-dynamics-v2/campaign.json"
DEFAULT_OUTPUT = ROOT / "reports/auto-research/hse-robustness"
DISTANCES = ("cosine", "hamming", "jaccard")
LINKAGES = ("single", "complete", "average")
CHECKPOINTS = (0, 10, 20)
BOOTSTRAP_SEED = 20260808
BOOTSTRAP_REPS = 1000


def behavioral_distance(left: Sequence[int], right: Sequence[int], distance: str) -> float:
    if len(left) != len(right):
        raise ValueError("behavioral vectors must have equal length")
    if distance == "cosine":
        ll, rr = sum(x * x for x in left), sum(x * x for x in right)
        if ll == rr == 0:
            return 0.0
        if ll == 0 or rr == 0:
            return 1.0
        return max(0.0, min(1.0, 1.0 - sum(x * y for x, y in zip(left, right)) / math.sqrt(ll * rr)))
    if distance == "hamming":
        return sum(x != y for x, y in zip(left, right)) / len(left)
    if distance == "jaccard":
        union = sum(bool(x or y) for x, y in zip(left, right))
        return 0.0 if union == 0 else 1.0 - sum(bool(x and y) for x, y in zip(left, right)) / union
    raise ValueError(f"unsupported distance: {distance}")


def normalized_hierarchical_diversity(matrix: Sequence[Sequence[int]], distance: str, linkage: str) -> float:
    """Exact entropy-over-height diversity for a deterministic agglomerative tree.

    This equals the project's HSE for cosine/single linkage, and extends its
    same normalized partition-entropy integral to complete/average linkage.
    """
    n = len(matrix)
    if n < 2:
        return 0.0
    if any(len(row) != len(matrix[0]) for row in matrix):
        raise ValueError("behavioral matrix is ragged")
    distances = [[0.0 for _ in range(n)] for _ in range(n)]
    for left in range(n):
        for right in range(left + 1, n):
            distances[left][right] = distances[right][left] = behavioral_distance(matrix[left], matrix[right], distance)
    clusters = [frozenset((index,)) for index in range(n)]
    events: list[tuple[float, frozenset[int], frozenset[int], frozenset[int]]] = []
    while len(clusters) > 1:
        candidates = []
        for left in range(len(clusters)):
            for right in range(left + 1, len(clusters)):
                values = [distances[i][j] for i in clusters[left] for j in clusters[right]]
                height = min(values) if linkage == "single" else max(values) if linkage == "complete" else sum(values) / len(values)
                candidates.append((height, tuple(sorted(clusters[left])), tuple(sorted(clusters[right])), left, right))
        height, _, _, left, right = min(candidates)
        a, b = clusters[left], clusters[right]
        merged = a | b
        events.append((height, merged, a, b))
        clusters = [cluster for index, cluster in enumerate(clusters) if index not in (left, right)] + [merged]
    active = [frozenset((index,)) for index in range(n)]
    def entropy() -> float:
        return -sum((len(cluster) / n) * math.log2(len(cluster) / n) for cluster in active)
    value = previous = 0.0
    event_index = 0
    while event_index < len(events) and events[event_index][0] <= 1e-12:
        _, merged, a, b = events[event_index]; active.remove(a); active.remove(b); active.append(merged); event_index += 1
    while event_index < len(events):
        height = events[event_index][0]
        value += entropy() * (height - previous)
        while event_index < len(events) and abs(events[event_index][0] - height) <= 1e-12:
            _, merged, a, b = events[event_index]; active.remove(a); active.remove(b); active.append(merged); event_index += 1
        previous = height
    return (value + entropy() * (1.0 - previous)) / math.log2(n)


def load_clean_v2(manifest_path: Path = DEFAULT_MANIFEST) -> dict[tuple[str, str, int, int], dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    runs = manifest["runs"]
    expected = {(router, condition, seed) for router in ("confidence", "random") for condition in ("private", "shared") for seed in range(1, 11)}
    observed = {(run["router"], run["condition"], int(run["seed"])) for run in runs}
    if len(runs) != 40 or observed != expected:
        raise ValueError("campaign manifest is not exactly the frozen 40-run clean-v2 2x2")
    result: dict[tuple[str, str, int, int], dict[str, Any]] = {}
    for run in runs:
        key = (run["router"], run["condition"], int(run["seed"]))
        lines = [json.loads(line) for line in (Path(run["run_dir"]) / "metrics.jsonl").read_text(encoding="utf-8").splitlines()]
        if {int(line["checkpoint"]) for line in lines} != set(CHECKPOINTS) or len(lines) != 3:
            raise ValueError(f"missing checkpoint matrices for {key}")
        for line in lines:
            matrix = line["behavioral_matrix"]
            if len(matrix) != 4 or any(len(row) != 40 for row in matrix):
                raise ValueError(f"expected 4x40 behavioral matrix for {key}")
            result[(*key, int(line["checkpoint"]))] = line
    if len(result) != 120:
        raise ValueError("expected exactly 120 checkpoint matrices")
    return result


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values)


def analyze(records: dict[tuple[str, str, int, int], dict[str, Any]], reps: int = BOOTSTRAP_REPS) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    table: list[dict[str, Any]] = []
    for distance in DISTANCES:
        for linkage in LINKAGES:
            for router in ("confidence", "random"):
                for checkpoint in CHECKPOINTS:
                    private = [normalized_hierarchical_diversity(records[(router, "private", seed, checkpoint)]["behavioral_matrix"], distance, linkage) for seed in range(1, 11)]
                    shared = [normalized_hierarchical_diversity(records[(router, "shared", seed, checkpoint)]["behavioral_matrix"], distance, linkage) for seed in range(1, 11)]
                    deltas = [a - b for a, b in zip(private, shared)]
                    table.append({"distance": distance, "linkage": linkage, "router": router, "checkpoint": checkpoint, "private_mean": _mean(private), "shared_mean": _mean(shared), "delta_private_minus_shared": _mean(deltas), "paired_positive_seeds": sum(value > 0 for value in deltas), "paired_seed_count": 10})
    rng = random.Random(BOOTSTRAP_SEED)
    sensitivity: list[dict[str, Any]] = []
    for distance in DISTANCES:
        for linkage in LINKAGES:
            for router in ("confidence", "random"):
                sampled: list[list[float]] = []
                within_sd: list[float] = []
                for seed in range(1, 11):
                    private = records[(router, "private", seed, 20)]["behavioral_matrix"]
                    shared = records[(router, "shared", seed, 20)]["behavioral_matrix"]
                    pv, sv = [], []
                    for _ in range(reps):
                        indices = [rng.randrange(40) for _ in range(40)]
                        pv.append(normalized_hierarchical_diversity([[row[i] for i in indices] for row in private], distance, linkage))
                        sv.append(normalized_hierarchical_diversity([[row[i] for i in indices] for row in shared], distance, linkage))
                    sampled.append([a - b for a, b in zip(pv, sv)])
                    within_sd.extend([math.sqrt(_mean((x - _mean(pv)) ** 2 for x in pv)), math.sqrt(_mean((x - _mean(sv)) ** 2 for x in sv))])
                boot = sorted(_mean(sampled[seed][rep] for seed in range(10)) for rep in range(reps))
                loo = []
                for omitted in range(40):
                    deltas = []
                    for seed in range(1, 11):
                        p = [[value for index, value in enumerate(row) if index != omitted] for row in records[(router, "private", seed, 20)]["behavioral_matrix"]]
                        s = [[value for index, value in enumerate(row) if index != omitted] for row in records[(router, "shared", seed, 20)]["behavioral_matrix"]]
                        deltas.append(normalized_hierarchical_diversity(p, distance, linkage) - normalized_hierarchical_diversity(s, distance, linkage))
                    loo.append(_mean(deltas))
                baseline = next(row["delta_private_minus_shared"] for row in table if row["distance"] == distance and row["linkage"] == linkage and row["router"] == router and row["checkpoint"] == 20)
                sensitivity.append({"distance": distance, "linkage": linkage, "router": router, "checkpoint": 20, "baseline_delta": baseline, "bootstrap_reps": reps, "bootstrap_rng_seed": BOOTSTRAP_SEED, "bootstrap_ci95_low": boot[int(0.025 * reps)], "bootstrap_ci95_high": boot[max(0, math.ceil(0.975 * reps) - 1)], "bootstrap_probability_positive": _mean(value > 0 for value in boot), "mean_within_run_bootstrap_sd": _mean(within_sd), "leave_one_probe_positive_count": sum(value > 0 for value in loo), "leave_one_probe_total": 40, "leave_one_probe_min_delta": min(loo), "leave_one_probe_max_delta": max(loo)})
    validation = max(abs(normalized_hierarchical_diversity(record["behavioral_matrix"], "cosine", "single") - float(record["normalized_hse"])) for record in records.values())
    return table, sensitivity, {"run_count": 40, "checkpoint_matrix_count": 120, "native_cosine_single_max_abs_error": validation, "bootstrap_rng_seed": BOOTSTRAP_SEED, "bootstrap_reps": reps}


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline frozen clean-v2 HSE robustness audit")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--bootstrap-reps", type=int, default=BOOTSTRAP_REPS)
    args = parser.parse_args()
    records = load_clean_v2(args.manifest)
    table, sensitivity, summary = analyze(records, args.bootstrap_reps)
    _write_csv(args.output / "checkpoint_hse_robustness.csv", table)
    _write_csv(args.output / "endpoint_probe_sensitivity.csv", sensitivity)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
