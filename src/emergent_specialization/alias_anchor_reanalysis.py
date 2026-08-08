"""Reproducible, offline alias and displayed-memory reanalysis.

This module deliberately reads immutable JSONL/manifest artifacts only.  It
does not construct clients, load credentials, or mutate raw run data.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "reports/auto-research/existing-data/alias-anchor-reanalysis"


def mean(values: Iterable[float]) -> float | None:
    values = list(values)
    return statistics.fmean(values) if values else None


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def is_modular_alias(probe: dict[str, Any], memory: list[dict[str, Any]], target_world: str) -> bool:
    """Exact residue overlap with a target-world exemplar only."""
    residue = (int(probe["x"]) % 7, int(probe["y"]) % 7)
    return any(item.get("world") == target_world and (int(item["x"]) % 7, int(item["y"]) % 7) == residue for item in memory)


def answer_probabilities(rows: list[dict[str, Any]]) -> dict[int, float]:
    n = len(rows)
    return {answer: sum(int(row["answer"]) == answer for row in rows) / n for answer in range(7)} if n else {}


def displayed_memory_metrics(answer: int, memory: list[dict[str, Any]], probabilities: dict[int, float], checkpoint: int) -> dict[str, float | int | None]:
    """Observed matches and a response-marginal conditional null for one row."""
    if not memory:
        return {"displayed_memory_size": 0, "distinct_label_coverage": 0.0, "mean_exposure_age": None,
                "any_label_match": None, "any_label_null": None, "last_label_match": None,
                "last_label_null": None, "last_prediction_match": None, "last_prediction_null": None}
    labels = [int(item["correct_answer"]) for item in memory]
    predictions = [int(item["prediction"]) for item in memory]
    label_set = set(labels)
    return {
        "displayed_memory_size": len(memory),
        "distinct_label_coverage": len(label_set) / 7,
        "mean_exposure_age": mean(float(checkpoint - int(item["round_id"])) for item in memory),
        "any_label_match": float(answer in label_set),
        "any_label_null": sum(probabilities.get(label, 0.0) for label in label_set),
        "last_label_match": float(answer == labels[-1]), "last_label_null": probabilities.get(labels[-1], 0.0),
        "last_prediction_match": float(answer == predictions[-1]), "last_prediction_null": probabilities.get(predictions[-1], 0.0),
    }


def calibration_rows(events: list[dict[str, Any]], protocol: str) -> list[dict[str, Any]]:
    result = []
    for event in events:
        if event.get("error") is not None or event.get("parsed_answer") is None:
            continue
        if protocol == "memory-representation-thinking-v1" and event.get("reasoning") != "off":
            continue
        context = event.get("context", {})
        memory = context.get("memory", context.get("truth_memory", []))
        probe = event["probe"]; target = str(event.get("target_world", probe["world"]))
        result.append({
            "protocol": protocol, "representation": event.get("representation") if protocol != "memory-learnability-v1" else None,
            "mode": event.get("mode"), "k": int(event.get("k", 0)), "context_seed": int(event["context_seed"]),
            "target_world": target, "probe_id": probe.get("task_id"), "replicate_id": event.get("replicate_id"),
            "alias": is_modular_alias(probe, memory, target), "answer": int(event["parsed_answer"]),
            "correct": float(event.get("correct", False)), "confidence": float(event.get("confidence", 0.0)),
        })
    return result


def calibration_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Responses are nested under a fixed generated context. First aggregate
    # response metrics inside each context-seed/alias stratum, then give each
    # present context stratum equal weight in the reported group mean.
    nested: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        nested[(row["protocol"], row["representation"], row["mode"], row["k"], row["context_seed"], row["alias"])].append(row)
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for key, values in nested.items():
        probs = answer_probabilities(values)
        groups[key[:-2] + (key[-1],)].append({"n": len(values), "accuracy": mean(v["correct"] for v in values), "confidence": mean(v["confidence"] for v in values), **{f"answer_{a}_share": probs[a] for a in range(7)}})
    out = []
    for key, values in sorted(groups.items(), key=str):
        out.append({"protocol": key[0], "representation": key[1], "mode": key[2], "k": key[3], "alias": key[4],
                    "context_seed_strata": len(values), "response_rows": sum(v["n"] for v in values),
                    "accuracy_context_mean": mean(v["accuracy"] for v in values), "confidence_context_mean": mean(v["confidence"] for v in values),
                    **{f"answer_{a}_share_context_mean": mean(v[f"answer_{a}_share"] for v in values) for a in range(7)}})
    return out


def clean_rows(manifest_path: Path) -> list[dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result = []
    for planned in manifest["runs"]:
        if planned.get("status") != "completed" or not planned.get("run_dir"):
            continue
        run_dir = Path(planned["run_dir"])
        event_path = run_dir / "events.jsonl"
        if not event_path.exists():
            continue
        for event in read_jsonl(event_path):
            if event.get("event") != "inference" or event.get("phase") != "probe" or event.get("error") is not None or event.get("parsed_answer") is None:
                continue
            result.append({"router": planned["router"], "condition": planned["condition"], "seed": int(planned["seed"]),
                           "run_id": run_dir.name, "checkpoint": int(event["checkpoint"]), "agent_id": event["agent_id"],
                           "probe_id": event.get("task", {}).get("task_id"), "answer": int(event["parsed_answer"]),
                           "memory": list(event.get("memory_inserted") or [])})
    return result


def clean_summary(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    seed_groups: dict[tuple[str, str, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows: seed_groups[(row["router"], row["condition"], row["checkpoint"], row["seed"])].append(row)
    seed_rows = []
    for key, values in sorted(seed_groups.items(), key=str):
        probs = answer_probabilities(values)
        metrics = [displayed_memory_metrics(v["answer"], v["memory"], probs, key[2]) for v in values]
        def m(name: str) -> float | None: return mean(float(item[name]) for item in metrics if item[name] is not None)
        seed_rows.append({"router": key[0], "condition": key[1], "checkpoint": key[2], "seed": key[3], "response_rows": len(values),
                          **{name: m(name) for name in ("displayed_memory_size", "distinct_label_coverage", "mean_exposure_age", "any_label_match", "any_label_null", "last_label_match", "last_label_null", "last_prediction_match", "last_prediction_null")}})
    groups: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in seed_rows: groups[(row["router"], row["condition"], row["checkpoint"])].append(row)
    out = []
    for key, values in sorted(groups.items(), key=str):
        row = {"router": key[0], "condition": key[1], "checkpoint": key[2], "seed_runs": len(values), "nested_response_rows": sum(v["response_rows"] for v in values)}
        for name in ("displayed_memory_size", "distinct_label_coverage", "mean_exposure_age", "any_label_match", "any_label_null", "last_label_match", "last_label_null", "last_prediction_match", "last_prediction_null"):
            row[name] = mean(float(v[name]) for v in values if v[name] is not None)
        for observed, null, excess in (("any_label_match", "any_label_null", "any_label_excess"), ("last_label_match", "last_label_null", "last_label_excess"), ("last_prediction_match", "last_prediction_null", "last_prediction_excess")):
            row[excess] = None if row[observed] is None else row[observed] - row[null]
        out.append(row)
    return seed_rows, out


def generate(output: str | Path = DEFAULT_OUTPUT, root: str | Path = ROOT) -> dict[str, Any]:
    root, output = Path(root), Path(output); output.mkdir(parents=True, exist_ok=True)
    calibration = calibration_rows(read_jsonl(root / "data/calibrations/memory-learnability-v1/events.jsonl"), "memory-learnability-v1")
    calibration += calibration_rows(read_jsonl(root / "data/calibrations/memory-representation-thinking-v1/events.jsonl"), "memory-representation-thinking-v1")
    write_csv(output / "calibration_alias_response_level.csv", calibration)
    write_csv(output / "calibration_alias_summary.csv", calibration_summary(calibration))
    clean = clean_rows(root / "data/campaigns/developmental-dynamics-v2/campaign.json")
    seed_rows, summary = clean_summary(clean)
    write_csv(output / "clean_displayed_memory_seed_level.csv", seed_rows)
    write_csv(output / "clean_displayed_memory_summary.csv", summary)
    metadata = {"status": "OFFLINE DESCRIPTIVE REANALYSIS", "calibration_success_rows": len(calibration), "clean_probe_response_rows": len(clean),
                "nesting": "Calibration summaries equal-weight present context_seed x alias strata; clean summaries equal-weight completed seed-runs, with probe-agent rows nested within each run.",
                "alias_definition": "Target-world-only exact (x mod 7, y mod 7) overlap between probe and an exemplar in displayed calibration context.",
                "clean_memory_definition": "Uses logged inference.memory_inserted (displayed recent-k context), never reconstructed full internal history.",
                "null_definition": "For each seed/router/condition/checkpoint, retain the empirical response-answer marginal p(a). Expected any-label match is sum_{a in displayed labels}p(a); last-label and last-prediction match use p(last value). Excess is observed minus that conditional expectation.",
                "shared_caution": "Support saturation can make this null equal the observed shared match rate; zero excess is not evidence against anchoring or copying."}
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"output": str(output), **metadata}


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline modular-alias and displayed-memory reanalysis")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT)); parser.add_argument("--root", default=str(ROOT)); args = parser.parse_args()
    print(json.dumps(generate(args.output, args.root), indent=2, sort_keys=True))


if __name__ == "__main__": main()
