"""Offline validation and K-estimation for completed Theory V1 MICRO raws."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from .. import observable_learner_calibration as learner
from .micro_estimation import estimate_k_explicit, estimate_k_pairwise, superposition_diagnostics
from .micro_runner import REPORT_ROOT, DATA_ROOT, stable_hash
from .micro_design import ECOLOGIES, K_VALUES, MICRO_SEEDS, double_swaps, single_swaps
from .prediction import predictions_for_k


def _manifest() -> dict[str, Any]:
    return json.loads((REPORT_ROOT / "micro_execution_manifest.json").read_text(encoding="utf-8"))


def _events() -> list[dict[str, Any]]:
    return learner._load_events(DATA_ROOT / "micro_events.jsonl")


def raw_sha256() -> str:
    digest = hashlib.sha256()
    with (DATA_ROOT / "micro_events.jsonl").open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def health() -> dict[str, Any]:
    manifest = _manifest()
    events = _events()
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        grouped[event["logical_id"]].append(event)
    terminal = {logical_id: rows[-1] for logical_id, rows in grouped.items() if any(row.get("terminal") for row in rows)}
    errors: defaultdict[str, int] = defaultdict(int)
    for event in events:
        category = event.get("error_category")
        if category:
            errors[str(category)] += 1
    models = sorted({(event.get("provider_metadata") or {}).get("model") for event in events})
    fingerprints = sorted({(event.get("provider_metadata") or {}).get("system_fingerprint") for event in events if (event.get("provider_metadata") or {}).get("system_fingerprint")})
    physical = len(events)
    logical = manifest["logical_calls"]
    retries = sum(int(event.get("attempt", 0)) for event in events)
    usage = sum(bool(event.get("token_usage")) for event in events)
    cost = sum(float(event.get("attempt_cost_usd") or 0.0) for event in events)
    return {
        "protocol": "THEORY-V1", "logical_expected": logical, "logical_terminal": len(terminal),
        "physical_attempts": physical, "technical_retries": retries,
        "error_categories": dict(errors), "semantic_ood": errors.get("out_of_domain", 0),
        "coverage": len(terminal) / logical if logical else 0.0,
        "models": models, "fingerprints": fingerprints,
        "usage_coverage": usage / physical if physical else 0.0,
        "observed_cost_usd": cost, "raw_sha256": raw_sha256() if (DATA_ROOT / "micro_events.jsonl").exists() else None,
        "classification": "CLEAN" if len(terminal) == logical and retries == 0 else ("COMPLETE_WITH_RETRIES" if len(terminal) == logical else "INCOMPLETE"),
        "duplicate_terminal_logical_ids": sum(1 for rows in grouped.values() if sum(bool(row.get("terminal")) for row in rows) > 1),
    }


def _terminal_rows() -> list[dict[str, Any]]:
    manifest = _manifest()
    events = _events()
    by_id: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        by_id[event["logical_id"]].append(event)
    rows = []
    for task in manifest["tasks"]:
        values = [event for event in by_id.get(task["logical_id"], []) if event.get("terminal")]
        if len(values) != 1:
            raise RuntimeError(f"logical id {task['logical_id']} has {len(values)} terminal observations")
        event = values[0]
        decisions = event.get("decisions")
        rows.append({
            "ecology": task["ecology"], "seed": int(task["seed"]), "k": int(task["k"]),
            "state_index": int(task["state_index"]), "state": task["state"], "target": int(task["target"]),
            "probe_index": int(task["probe_index"]), "correct": int(decisions == task["probe"]["y"]) if decisions is not None else 0,
            "decisions": decisions, "expected": task["probe"]["y"], "logical_id": task["logical_id"],
            "latency_s": event.get("latency_s"), "cost_usd": event.get("attempt_cost_usd"),
            "error_category": event.get("error_category") or "",
        })
    return rows


def analyze_micro() -> dict[str, Any]:
    """Estimate K from completed raws and write all MICRO-only artifacts."""
    manifest = _manifest()
    health_result = health()
    if health_result["classification"] == "INCOMPLETE":
        raise RuntimeError(f"MICRO health incomplete: {health_result}")
    rows = _terminal_rows()
    out = REPORT_ROOT / "micro-analysis"
    out.mkdir(parents=True, exist_ok=True)
    with (out / "response_level.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["ecology", "seed", "k", "state_index", "state", "target", "probe_index", "correct", "decisions", "expected", "logical_id", "latency_s", "cost_usd", "error_category"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "decisions": json.dumps(row["decisions"], separators=(",", ":")), "expected": json.dumps(row["expected"], separators=(",", ":"))})

    # Accuracy vectors a(state) have one entry per target niche.  The baseline
    # is state 0; all deltas below are therefore competence changes relative to
    # the same unit's balanced memory.
    grouped: dict[tuple[str, int, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["ecology"], row["seed"], row["k"], row["state_index"])].append(row)
    k_rows: list[dict[str, Any]] = []
    linearity_rows: list[dict[str, Any]] = []
    matrices: dict[str, dict[str, list[list[float]]]] = {}
    for ecology in ECOLOGIES:
        matrices[ecology] = {}
        for seed in MICRO_SEEDS[ecology]:
            for k in K_VALUES:
                base_values = [statistics.mean(row["correct"] for row in grouped[(ecology, seed, k, 0)] if row["target"] == target) for target in range(4)]
                responses: list[np.ndarray] = []
                swap_vectors: list[np.ndarray] = []
                for index, swap in enumerate(single_swaps(seed, k)):
                    values = [statistics.mean(row["correct"] for row in grouped[(ecology, seed, k, index + 1)] if row["target"] == target) for target in range(4)]
                    responses.append(np.asarray(values) - np.asarray(base_values))
                    delta = np.zeros(4); delta[int(swap["target"])] += 1.0; delta[int(swap["source"])] -= 1.0
                    swap_vectors.append(delta)
                    for target, value in enumerate(values):
                        k_rows.append({"ecology": ecology, "seed": seed, "k": k, "state": f"single_{index:02d}", "source": swap["source"], "target": swap["target"], "competence": value, "baseline": base_values[target], "delta": value - base_values[target]})
                explicit = estimate_k_explicit(swap_vectors, responses)
                pairwise = estimate_k_pairwise(swap_vectors, responses)
                key = f"{ecology}:{seed}:{k}"
                matrices[ecology][key] = explicit.tolist()
                linearity_errors = []
                for index, pair in enumerate(double_swaps(seed, k)):
                    state_index = 13 + index
                    actual = np.asarray([statistics.mean(row["correct"] for row in grouped[(ecology, seed, k, state_index)] if row["target"] == target) for target in range(4)]) - np.asarray(base_values)
                    first = single_swaps(seed, k).index(pair[0]); second = single_swaps(seed, k).index(pair[1])
                    predicted = responses[first] + responses[second]
                    linearity_errors.append(float(np.max(np.abs(actual - predicted))))
                linearity_rows.append({"ecology": ecology, "seed": seed, "k": k, "max_double_swap_error": max(linearity_errors), "mean_double_swap_error": statistics.mean(linearity_errors)})
                k_rows.append({"ecology": ecology, "seed": seed, "k": k, "state": "K_SUMMARY", "source": "", "target": "", "competence": "", "baseline": "", "delta": json.dumps({"explicit": explicit.tolist(), "pairwise": pairwise.tolist(), "max_estimator_diff": float(np.max(np.abs(explicit - pairwise)))})})
    with (out / "k_estimates.json").open("w", encoding="utf-8") as handle:
        json.dump(matrices, handle, indent=2, sort_keys=True); handle.write("\n")
    with (out / "competence_deltas.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = sorted({key for row in k_rows for key in row})
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(k_rows)
    with (out / "superposition.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = sorted({key for row in linearity_rows for key in row})
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(linearity_rows)
    result = {
        "protocol": "THEORY-V1", "status": "MICRO_COMPLETE_ANALYZED", "health": health_result,
        "units": len(matrices[ECOLOGIES[0]]) + len(matrices[ECOLOGIES[1]]),
        "k_estimates": str(out / "k_estimates.json"), "superposition": str(out / "superposition.csv"),
        "manifest_tasks_hash": manifest["tasks_hash"],
    }
    with (out / "micro_analysis.json").open("w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True); handle.write("\n")
    return result


def generate_predictions() -> dict[str, Any]:
    """Mechanically produce the frozen macro registry from completed K estimates."""
    health_result = health()
    if health_result["classification"] == "INCOMPLETE":
        raise RuntimeError("cannot generate predictions from incomplete MICRO")
    path = REPORT_ROOT / "micro-analysis" / "k_estimates.json"
    matrices = json.loads(path.read_text(encoding="utf-8"))
    predictions = []
    for ecology, values in matrices.items():
        for key, matrix in values.items():
            seed = int(key.split(":")[1]); k = int(key.split(":")[2])
            for row in predictions_for_k(np.asarray(matrix, dtype=float), k):
                predictions.append({"ecology": ecology, "seed": seed, **row})
    output = {"protocol": "THEORY-V1", "status": "PREDICTIONS_GENERATED_AFTER_MICRO", "predictions": predictions, "micro_raw_sha256": health_result["raw_sha256"]}
    atomic_path = REPORT_ROOT / "prediction_manifest.json"
    with atomic_path.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2, sort_keys=True); handle.write("\n")
    return output
