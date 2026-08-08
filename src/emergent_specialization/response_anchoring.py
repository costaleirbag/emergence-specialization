"""Offline response-anchoring and behavioral-synchronization diagnostics.

These measures are descriptive. They quantify whether a response repeats labels
or predictions present in the current controlled memory; they do not establish
causality or useful rule induction.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from .analysis import _load_jsonl

ROOT = Path(__file__).resolve().parents[2]
V2_ROOT = ROOT / "data/runs/campaigns/developmental-dynamics-v2"
OUT = ROOT / "reports/response-anchoring"


def _mean(values: Iterable[float]) -> float | None:
    vals = list(values); return statistics.fmean(vals) if vals else None


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields: fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore"); writer.writeheader(); writer.writerows(rows)


def anchoring_metrics(answer: int | None, memory: list[dict[str, Any]]) -> dict[str, float | None]:
    """Return anchoring indicators for one response and immutable memory list."""
    if answer is None or not memory:
        return {"last_prediction": None, "last_label": None, "any_prediction": None, "any_label": None, "modal_label": None}
    predictions = [item.get("prediction") for item in memory]
    labels = [item.get("correct_answer") for item in memory]
    counts = {label: labels.count(label) for label in set(labels)}
    modal = min(counts, key=lambda label: (-counts[label], label))
    return {"last_prediction": float(answer == predictions[-1]), "last_label": float(answer == labels[-1]), "any_prediction": float(answer in predictions), "any_label": float(answer in labels), "modal_label": float(answer == modal)}


def _memory_for_event(event: dict[str, Any]) -> list[dict[str, Any]]:
    inserted = event.get("memory_inserted")
    return list(inserted) if isinstance(inserted, list) else []


def _run_rows(run_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
    config = metadata.get("config", {}); condition = config.get("condition", {}).get("memory_mode", "unknown")
    router = config.get("router", {}).get("strategy", "unknown"); seed = config.get("experiment", {}).get("seed")
    events = _load_jsonl(run_dir / "events.jsonl")
    rows: list[dict[str, Any]] = []
    for event in events:
        if event.get("event") != "inference" or event.get("error") is not None or event.get("parsed_answer") is None: continue
        memory = _memory_for_event(event); metrics = anchoring_metrics(int(event["parsed_answer"]), memory)
        rows.append({"run_id": metadata.get("run_id", run_dir.name), "condition": condition, "router": router, "seed": seed, "phase": event.get("phase"), "round": event.get("round_id"), "checkpoint": event.get("checkpoint"), "world": (event.get("task") or {}).get("world"), "correct": float(event.get("parsed_answer") == (event.get("task") or {}).get("correct_answer")), "confidence": event.get("confidence"), "memory_count": len(memory), **metrics})
    # Pairwise answer agreement among agents for each probe/task at a checkpoint.
    probe_groups: dict[tuple[Any, Any], list[int]] = defaultdict(list)
    for row, event in zip(rows, [e for e in events if e.get("event") == "inference" and e.get("error") is None and e.get("parsed_answer") is not None]):
        if row["phase"] == "probe": probe_groups[(row["checkpoint"], (event.get("task") or {}).get("task_id"))].append(int(event["parsed_answer"]))
    agreement: list[dict[str, Any]] = []
    for (checkpoint, task_id), answers in sorted(probe_groups.items(), key=str):
        if len(answers) < 2: continue
        pairs = len(answers) * (len(answers) - 1) // 2
        agreement.append({"run_id": rows[0]["run_id"] if rows else run_dir.name, "condition": condition, "router": router, "seed": seed, "checkpoint": checkpoint, "task_id": task_id, "pairwise_answer_agreement": sum(answers[i] == answers[j] for i in range(len(answers)) for j in range(i + 1, len(answers))) / pairs, "agent_count": len(answers)})
    return rows, agreement


def generate(v2_root: str | Path = V2_ROOT, output: str | Path = OUT) -> dict[str, Any]:
    v2_root, output = Path(v2_root), Path(output); rows: list[dict[str, Any]] = []; agreements: list[dict[str, Any]] = []
    for run_dir in sorted(p for p in v2_root.iterdir() if p.is_dir() and (p / "events.jsonl").exists()):
        current, pair = _run_rows(run_dir); rows.extend(current); agreements.extend(pair)
    _write_csv(output / "clean_v2_anchoring_response_level.csv", rows); _write_csv(output / "clean_v2_probe_pairwise_agreement.csv", agreements)
    summary: list[dict[str, Any]] = []
    keys = ("last_prediction", "last_label", "any_label", "modal_label")
    sorted_rows = sorted(rows, key=lambda r: (r["router"], r["condition"], r["phase"], str(r["checkpoint"])))
    for group, values in itertools.groupby(sorted_rows, key=lambda r: (r["router"], r["condition"], r["phase"], str(r["checkpoint"]))):
        values = list(values); summary.append({"router": group[0], "condition": group[1], "phase": group[2], "checkpoint": group[3], "n": len(values), **{key: _mean(float(v[key]) for v in values if v[key] is not None) for key in keys}, "accuracy_when_last_label_anchored": _mean(float(v["correct"]) for v in values if v["last_label"] == 1.0), "accuracy_when_not_last_label_anchored": _mean(float(v["correct"]) for v in values if v["last_label"] == 0.0), "confidence_when_last_label_anchored": _mean(float(v["confidence"]) for v in values if v["last_label"] == 1.0), "confidence_when_not_last_label_anchored": _mean(float(v["confidence"]) for v in values if v["last_label"] == 0.0)})
    _write_csv(output / "clean_v2_anchoring_summary.csv", summary)
    return {"status": "OFFLINE DESCRIPTIVE AUDIT", "response_rows": len(rows), "probe_agreement_rows": len(agreements), "summary_rows": len(summary), "output": str(output)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline response anchoring audit")
    parser.add_argument("--output", default=str(OUT)); args = parser.parse_args(); print(json.dumps(generate(output=args.output), indent=2))


if __name__ == "__main__": main()
