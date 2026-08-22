"""Offline report for memory-representation-thinking-v1.

Only successful events using the final configured output cap are included in
factorial summaries. Incomplete thinking calls remain visible in health tables.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = ROOT / "data/calibrations/memory-representation-thinking-v1"
DEFAULT_OUTPUT = ROOT / "reports/calibrations/memory-representation-thinking-v1"


def _mean(values: list[float]) -> float | None: return statistics.fmean(values) if values else None
def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields: fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore"); writer.writeheader(); writer.writerows(rows)


def _rank(values: list[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda item: item[1]); result = [0.0] * len(values); i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and ordered[j][1] == ordered[i][1]: j += 1
        rank = (i + j - 1) / 2 + 1
        for index, _ in ordered[i:j]: result[index] = rank
        i = j
    return result


def _corr(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2 or len(xs) != len(ys): return None
    mx, my = statistics.fmean(xs), statistics.fmean(ys); den = math.sqrt(sum((x-mx)**2 for x in xs) * sum((y-my)**2 for y in ys))
    return sum((x-mx)*(y-my) for x, y in zip(xs, ys)) / den if den else None


def _auc(scores: list[float], labels: list[bool]) -> float | None:
    pos = [s for s, label in zip(scores, labels) if label]; neg = [s for s, label in zip(scores, labels) if not label]
    if not pos or not neg: return None
    return sum(1.0 if p > n else 0.5 if p == n else 0.0 for p in pos for n in neg) / (len(pos) * len(neg))


def _anchor(event: dict[str, Any]) -> dict[str, float | None]:
    memory = event.get("rendered_memory") or []; answer = event.get("parsed_answer")
    if not memory or answer is None: return {"last_prediction": None, "last_label": None, "any_label": None, "modal_label": None}
    labels = [item.get("correct_answer") for item in memory]; predictions = [item.get("prediction") for item in memory if "prediction" in item]; counts = {label: labels.count(label) for label in set(labels)}; modal = min(counts, key=lambda label: (-counts[label], label))
    return {"last_prediction": float(bool(predictions) and answer == predictions[-1]), "last_label": float(answer == labels[-1]), "any_label": float(answer in labels), "modal_label": float(answer == modal)}


def generate(input_dir: str | Path = DEFAULT_INPUT, output_dir: str | Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    input_dir, output_dir = Path(input_dir), Path(output_dir); output_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((input_dir / "manifest.json").read_text(encoding="utf-8")); events = [json.loads(line) for line in (input_dir / "events.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    final_cap = int(manifest.get("thinking_max_tokens", 2048)); valid = [e for e in events if e.get("error") is None and e.get("parsed_answer") is not None and (e.get("reasoning") != "high" or int(e.get("max_tokens", 0)) == final_cap)]
    response_rows: list[dict[str, Any]] = []
    for event in valid:
        representations = ("full_experience", "feedback_only") if event.get("representation") == "common_k0" else (event.get("representation"),)
        for rep in representations:
            anchor = _anchor(event); response_rows.append({"reasoning": event.get("reasoning"), "representation": rep, "mode": event.get("mode"), "world": event.get("target_world"), "k": event.get("k"), "context_seed": event.get("context_seed"), "probe_id": (event.get("probe") or {}).get("task_id"), "replicate": event.get("replicate_id"), "answer": event.get("parsed_answer"), "correct": float(event.get("correct", False)), "confidence": event.get("confidence"), "prompt_hash": event.get("prompt_hash"), "max_tokens": event.get("max_tokens"), **anchor})
    _write_csv(output_dir / "response_level.csv", response_rows)
    contexts: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in response_rows: contexts[(row["reasoning"], row["representation"], row["mode"], row["world"], int(row["k"]), int(row["context_seed"]))].append(row)
    context_rows: list[dict[str, Any]] = []
    for key, rows in sorted(contexts.items(), key=str):
        labels = [bool(r["correct"]) for r in rows]; conf = [float(r["confidence"]) for r in rows]; anchor = [r for r in rows if r["last_label"] is not None]
        context_rows.append({"reasoning": key[0], "representation": key[1], "mode": key[2], "world": key[3], "k": key[4], "context_seed": key[5], "n": len(rows), "accuracy": _mean([float(x) for x in labels]), "mean_confidence": _mean(conf), "confidence_when_correct": _mean([float(r["confidence"]) for r in rows if r["correct"]]), "confidence_when_incorrect": _mean([float(r["confidence"]) for r in rows if not r["correct"]]), "confidence_point_biserial": _corr(conf, [float(x) for x in labels]), "confidence_spearman": _corr(_rank(conf), _rank([float(x) for x in labels])), "confidence_auc": _auc(conf, labels), "brier": _mean([(c-float(y))**2 for c, y in zip(conf, labels)]), "last_label_anchoring": _mean([float(r["last_label"]) for r in anchor]), "any_label_anchoring": _mean([float(r["any_label"]) for r in anchor]), "accuracy_anchored": _mean([float(r["correct"]) for r in anchor if r["last_label"] == 1.0]), "accuracy_unanchored": _mean([float(r["correct"]) for r in anchor if r["last_label"] == 0.0])})
    _write_csv(output_dir / "context_level.csv", context_rows)
    curves: list[dict[str, Any]] = []
    for key, rows in __import__("itertools").groupby(sorted(context_rows, key=lambda r: (r["reasoning"], r["representation"], r["mode"], int(r["k"]))), key=lambda r: (r["reasoning"], r["representation"], r["mode"], int(r["k"]))):
        rows = list(rows); curves.append({"reasoning": key[0], "representation": key[1], "mode": key[2], "k": key[3], "contexts": len(rows), "accuracy": _mean([float(r["accuracy"]) for r in rows]), "confidence": _mean([float(r["mean_confidence"]) for r in rows]), "anchoring": _mean([float(r["last_label_anchoring"]) for r in rows if r["last_label_anchoring"] is not None]), "confidence_auc": _mean([float(r["confidence_auc"]) for r in rows if r["confidence_auc"] is not None])})
    _write_csv(output_dir / "learning_curves.csv", curves)
    reliability: list[dict[str, Any]] = []
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in response_rows: groups[(row["reasoning"], row["representation"], row["mode"], row["world"], row["k"], row["context_seed"], row["probe_id"])].append(row)
    for key, rows in sorted(groups.items(), key=str):
        answers = [r["answer"] for r in sorted(rows, key=lambda r: int(r["replicate"]))]; correctness = [bool(r["correct"]) for r in rows]; conf = [float(r["confidence"]) for r in rows]; pairs = len(rows) * (len(rows)-1) // 2
        reliability.append({"reasoning": key[0], "representation": key[1], "mode": key[2], "world": key[3], "k": key[4], "context_seed": key[5], "probe_id": key[6], "replicates": len(rows), "exact_3way_answer_agreement": float(len(rows) == 3 and len(set(answers)) == 1), "pairwise_answer_agreement": sum(answers[i] == answers[j] for i in range(len(answers)) for j in range(i+1, len(answers))) / pairs if pairs else None, "exact_3way_correctness_agreement": float(len(rows) == 3 and len(set(correctness)) == 1), "pairwise_correctness_agreement": sum(correctness[i] == correctness[j] for i in range(len(correctness)) for j in range(i+1, len(correctness))) / pairs if pairs else None, "confidence_variance": statistics.pvariance(conf) if len(conf) > 1 else None})
    _write_csv(output_dir / "reliability.csv", reliability)
    _write_csv(output_dir / "anchoring.csv", [row for row in context_rows if row["last_label_anchoring"] is not None])
    probe_manifest = json.loads((input_dir / "balanced_probe_set.json").read_text(encoding="utf-8")); _write_csv(output_dir / "balanced_probe_manifest.csv", probe_manifest["tasks"])
    health = {"physical_attempts": len(events), "valid_factorial_completions": len(valid), "errors": {}, "semantic_ood": sum(e.get("semantic_violation") is not None for e in events), "cost_usd": sum(float(e.get("observed_cost_usd", 0.0)) for e in events)}
    for event in events:
        if event.get("error_category"): health["errors"][event["error_category"]] = health["errors"].get(event["error_category"], 0) + 1
    report = {"protocol": manifest.get("protocol"), "status": "PARTIAL — thinking-on blocked by output/cost guard; offline report", "planned_logical_queries": manifest.get("planned_logical_queries"), "off_logical_complete": len({e.get("query_id") for e in valid if e.get("reasoning") == "off"}), "thinking_on_valid_logical": len({e.get("query_id") for e in valid if e.get("reasoning") == "high" and int(e.get("max_tokens", 0)) == final_cap}), "valid_factorial_rows": len(response_rows), "final_thinking_cap": final_cap, "health": health, "probe_hash": manifest.get("probe_hash"), "generated_at_utc": datetime.now(UTC).isoformat(), "scientific_status": "DESCRIPTIVE CALIBRATION; NOT SOCIETY EVIDENCE"}
    _write_json(output_dir / "summary.json", report); return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline memory representation x thinking report"); parser.add_argument("--input", default=str(DEFAULT_INPUT)); parser.add_argument("--output", default=str(DEFAULT_OUTPUT)); args = parser.parse_args(); print(json.dumps(generate(args.input, args.output), indent=2, sort_keys=True))


if __name__ == "__main__": main()
