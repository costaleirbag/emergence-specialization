"""Offline overnight audit for clean v2 and memory-learnability-v1.

This command only reads existing artifacts.  It creates paired endpoint
contrasts, checkpoint summaries, leave-one-seed-out sensitivity, and a concise
machine-readable inventory.  It intentionally performs no inferential tests.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from emergent_specialization.runtime.health import run_health

ROOT = Path(__file__).resolve().parents[3]
CAMPAIGN_REPORT = ROOT / "reports/campaigns/developmental-dynamics-v2/clean-2x2"
OUTPUT = ROOT / "reports/overnight"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle: return list(csv.DictReader(handle))


def _mean(values: list[float]) -> float | None: return statistics.fmean(values) if values else None


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields: fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore"); writer.writeheader(); writer.writerows(rows)


def generate(output: str | Path = OUTPUT) -> dict[str, Any]:
    output = Path(output).resolve(); output.mkdir(parents=True, exist_ok=True)
    checkpoints = _read_csv(CAMPAIGN_REPORT / "checkpoint_metrics.csv")
    by: dict[tuple[str, str, int], list[dict[str, str]]] = defaultdict(list)
    for row in checkpoints: by[(row["cell"], row["seed"], int(row["checkpoint"]))].append(row)
    endpoint: list[dict[str, Any]] = []
    for cell in sorted({r["cell"] for r in checkpoints}):
        for seed in sorted({r["seed"] for r in checkpoints}, key=int):
            zero = by.get((cell, seed, 0), [{}])[0]; final = by.get((cell, seed, 20), [{}])[0]
            endpoint.append({"cell": cell, "seed": int(seed), "delta_hse": float(final.get("normalized_hse", 0)) - float(zero.get("normalized_hse", 0)), "delta_phi": float(final.get("phi", 0)) - float(zero.get("phi", 0)), "hse_0": float(zero.get("normalized_hse", 0)), "hse_20": float(final.get("normalized_hse", 0)), "phi_0": float(zero.get("phi", 0)), "phi_20": float(final.get("phi", 0)), "oracle_gain_20": float(final.get("oracle_gain", 0)), "eta_route_20": final.get("routing_alignment_eta")})
    _write_csv(output / "clean_v2_endpoint_deltas.csv", endpoint)
    paired: list[dict[str, Any]] = []
    for router in ("confidence", "random"):
        for metric in ("delta_hse", "delta_phi"):
            for seed in range(1, 11):
                p = next(r for r in endpoint if r["cell"] == f"{router}/private" and r["seed"] == seed)
                s = next(r for r in endpoint if r["cell"] == f"{router}/shared" and r["seed"] == seed)
                paired.append({"router": router, "seed": seed, "metric": metric, "private": p[metric], "shared": s[metric], "private_minus_shared": p[metric] - s[metric]})
    _write_csv(output / "paired_endpoint_contrasts.csv", paired)
    leave_one_out: list[dict[str, Any]] = []
    for router in ("confidence", "random"):
        for metric in ("delta_hse", "delta_phi"):
            values = [r["private_minus_shared"] for r in paired if r["router"] == router and r["metric"] == metric]
            for omitted in range(1, 11):
                subset = [v for seed, v in enumerate(values, 1) if seed != omitted]
                leave_one_out.append({"router": router, "metric": metric, "omitted_seed": omitted, "mean_contrast": _mean(subset)})
    _write_csv(output / "jackknife_contrasts.csv", leave_one_out)
    summary = {"generated_at_utc": datetime.now(UTC).isoformat(), "status": "OFFLINE DESCRIPTIVE AUDIT", "clean_v2_endpoint_means": {}, "probe_subsampling": "not recomputed here; existing fixed 40-probe checkpoint metrics retained", "scientific_caution": "No causal or confirmatory conclusion; calibration and clean v2 are separate datasets."}
    for cell in sorted({r["cell"] for r in endpoint}):
        rows = [r for r in endpoint if r["cell"] == cell]
        summary["clean_v2_endpoint_means"][cell] = {key: _mean([float(r[key]) for r in rows]) for key in ("delta_hse", "delta_phi", "hse_0", "hse_20", "phi_0", "phi_20", "oracle_gain_20")}
    (output / "overnight_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline overnight research audit")
    parser.add_argument("--output", default=str(OUTPUT)); args = parser.parse_args(); print(json.dumps(generate(args.output), indent=2, sort_keys=True))


if __name__ == "__main__": main()
