"""Offline analysis for the memory-learnability-v1 calibration.

The calibration is deliberately analysed separately from society runs.  This
module reads only the append-only calibration JSONL and emits tidy CSV/JSON and
small dependency-free SVGs.  It never contacts a provider.
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
from typing import Any, Iterable

from .metrics.differentiation import (
    competence_differentiation_phi,
    division_of_labor_matching,
    routing_alignment,
)
from .metrics.hse import hierarchic_social_entropy

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "data/calibrations/memory-learnability-v1"
DEFAULT_OUTPUT = ROOT / "reports/calibrations/memory-learnability-v1"


def _mean(values: Iterable[float]) -> float | None:
    vals = list(values)
    return statistics.fmean(vals) if vals else None


def _sd(values: Iterable[float]) -> float | None:
    vals = list(values)
    return statistics.stdev(vals) if len(vals) > 1 else None


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def _rank(values: list[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and ordered[j][1] == ordered[i][1]: j += 1
        rank = (i + j - 1) / 2 + 1
        for index, _ in ordered[i:j]: ranks[index] = rank
        i = j
    return ranks


def _corr(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2: return None
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    den = math.sqrt(sum((x-mx)**2 for x in xs) * sum((y-my)**2 for y in ys))
    return sum((x-mx)*(y-my) for x, y in zip(xs, ys)) / den if den else None


def _auc(scores: list[float], labels: list[bool]) -> float | None:
    pos = [(s, y) for s, y in zip(scores, labels) if y]
    neg = [(s, y) for s, y in zip(scores, labels) if not y]
    if not pos or not neg: return None
    wins = sum(1.0 if p > n else 0.5 if p == n else 0.0 for p, _ in pos for n, _ in neg)
    return wins / (len(pos) * len(neg))


def _pairwise_agreement(values: list[Any]) -> float | None:
    if len(values) < 2:
        return None
    pairs = len(values) * (len(values) - 1) // 2
    return sum(values[i] == values[j] for i in range(len(values)) for j in range(i + 1, len(values))) / pairs


def _display_mode(mode: str) -> str:
    # Historical raw events used this name, but the payload contained truthful
    # corrective feedback after a wrong previous prediction. It was never a
    # corrupted-label control. Raw JSONL is immutable; only analysis labels are
    # corrected here.
    return "wrong_prediction_with_correct_feedback_k8" if mode == "corrupted_k8" else mode


def _anchoring(event: dict[str, Any]) -> dict[str, Any]:
    answer = event.get("parsed_answer")
    memory = event.get("context", {}).get("memory", [])
    if answer is None or not memory:
        return {"last_prediction": None, "last_label": None, "any_prediction": None, "any_label": None, "modal_label": None}
    predictions = [item.get("prediction") for item in memory]
    labels = [item.get("correct_answer") for item in memory]
    counts = {label: labels.count(label) for label in set(labels)}
    modal = min(counts, key=lambda label: (-counts[label], label))
    return {"last_prediction": float(answer == predictions[-1]), "last_label": float(answer == labels[-1]), "any_prediction": float(answer in predictions), "any_label": float(answer in labels), "modal_label": float(answer == modal)}


def _svg_line(path: Path, series: dict[str, list[tuple[float, float]]], title: str, y_label: str) -> None:
    width, height = 920, 500; left, top, right, bottom = 90, 55, 30, 65
    points = [p for seq in series.values() for p in seq]
    xs = [p[0] for p in points] or [0, 1]; ys = [p[1] for p in points] or [0, 1]
    xmin, xmax = min(xs), max(xs); ymin, ymax = min(ys), max(ys)
    if xmax == xmin: xmax = xmin + 1
    if ymax == ymin: ymax = ymin + 1
    sx = lambda x: left + (x-xmin)/(xmax-xmin)*(width-left-right)
    sy = lambda y: height-bottom - (y-ymin)/(ymax-ymin)*(height-top-bottom)
    colors = ["#264653", "#e76f51", "#2a9d8f", "#8c6bb1", "#f4a261", "#457b9d"]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="#fffdf8"/>',
           f'<text x="{left}" y="32" font-family="sans-serif" font-size="21" font-weight="700">{title}</text>',
           f'<text x="18" y="{height/2}" transform="rotate(-90 18 {height/2})" font-family="sans-serif" font-size="13">{y_label}</text>',
           f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#333"/><line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#333"/>']
    for i, (label, seq) in enumerate(series.items()):
        color = colors[i % len(colors)]; coords = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in seq)
        out.append(f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{coords}"/>')
        for x, y in seq: out.append(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="3" fill="{color}"/>')
        lx = left + i * 150; out.append(f'<line x1="{lx}" y1="{height-25}" x2="{lx+20}" y2="{height-25}" stroke="{color}" stroke-width="4"/><text x="{lx+26}" y="{height-20}" font-family="sans-serif" font-size="12">{label}</text>')
    out.append("</svg>"); path.parent.mkdir(parents=True, exist_ok=True); path.write_text("\n".join(out), encoding="utf-8")


def _manual_positive_control(summary_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Construct a labelled analysis-only control from calibration outputs.

    This is not a society run: each world column is assigned to the agent with
    the strongest calibrated same-world response.  It is intentionally labelled
    synthetic, so it cannot be mistaken for emergent evidence.
    """
    worlds = ("ALPHA", "BETA", "GAMMA", "DELTA"); agents = tuple(f"agent_{i}" for i in range(4))
    competence = {agent: {} for agent in agents}; routing = {world: {} for world in worlds}
    for wi, world in enumerate(worlds):
        row = next((r for r in summary_rows if r["mode"] == "same_world" and r["world"] == world and int(r["k"]) == 8), None)
        score = float(row["accuracy"]) if row else 0.0
        # deterministic synthetic specialist permutation; calibration scores
        # supply the competency level, not a claim about agent identities.
        specialist = agents[wi]
        for agent in agents: competence[agent][world] = score if agent == specialist else max(0.0, score * 0.35)
        routing[world] = {agent: (10 if agent == specialist else 0) for agent in agents}
    matrix = [[competence[a][w] for w in worlds] for a in agents]
    hse = hierarchic_social_entropy([[int(round(v*100)) for v in row] for row in matrix])
    match = division_of_labor_matching(competence)
    return {"label": "SYNTHETIC POSITIVE CONTROL — NOT SOCIETY DATA", "competence": competence, "phi": competence_differentiation_phi(matrix), "normalized_hse": hse["normalized_hse"], "matching": match, "routing_alignment": routing_alignment(routing, competence)}


def generate(input_dir: str | Path = DEFAULT_INPUT, output_dir: str | Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    input_dir, output_dir = Path(input_dir).resolve(), Path(output_dir).resolve(); output_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((input_dir / "manifest.json").read_text(encoding="utf-8"))
    events = [json.loads(line) for line in (input_dir / "events.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    completions = [e for e in events if e.get("event") == "completion" and e.get("error") is None]
    # Reliability is defined over identical prompts/probes, not over all probes
    # in a context. The old report accidentally mixed ten distinct probes with
    # three replicates.
    groups: dict[tuple[str, str, int, int, str], list[dict[str, Any]]] = defaultdict(list)
    for event in completions:
        probe_id = str((event.get("probe") or {}).get("task_id") or event.get("prompt_hash"))
        groups[(str(event["mode"]), str(event["target_world"]), int(event["k"]), int(event["context_seed"]), probe_id)].append(event)
    summary_rows: list[dict[str, Any]] = []
    context_groups: dict[tuple[str, str, int, int], list[dict[str, Any]]] = defaultdict(list)
    for (mode, world, k, seed, _probe), rows in groups.items(): context_groups[(mode, world, k, seed)].extend(rows)
    for (mode, world, k, seed), rows in sorted(context_groups.items()):
        labels = [bool(row.get("correct")) for row in rows]; conf = [float(row.get("confidence", 0.0)) for row in rows]
        anchor_rows = [_anchoring(row) for row in rows]
        summary_rows.append({"mode": _display_mode(mode), "raw_mode": mode, "world": world, "k": k, "context_seed": seed, "n": len(rows), "accuracy": _mean(labels), "accuracy_sd": _sd([float(v) for v in labels]), "mean_confidence": _mean(conf), "confidence_sd": _sd(conf), "confidence_accuracy_r": _corr(conf, [float(v) for v in labels]), "confidence_accuracy_spearman": _corr(_rank(conf), _rank([float(v) for v in labels])), "confidence_auc": _auc(conf, labels), "brier": _mean([(c-float(y))**2 for c, y in zip(conf, labels)]), "last_label_anchoring": _mean(float(row["last_label"]) for row in anchor_rows if row["last_label"] is not None), "any_label_anchoring": _mean(float(row["any_label"]) for row in anchor_rows if row["any_label"] is not None), "accuracy_anchored_last_label": _mean(float(row.get("correct")) for row, anchor in zip(rows, anchor_rows) if anchor["last_label"] == 1.0), "accuracy_unanchored_last_label": _mean(float(row.get("correct")) for row, anchor in zip(rows, anchor_rows) if anchor["last_label"] == 0.0)})
    _write_csv(output_dir / "learnability_by_context.csv", summary_rows)
    curve_rows = []
    for mode in sorted({r["mode"] for r in summary_rows}):
        for k in sorted({r["k"] for r in summary_rows if r["mode"] == mode}):
            rows = [r for r in summary_rows if r["mode"] == mode and r["k"] == k]
            curve_rows.append({"mode": mode, "k": k, "contexts": len(rows), "accuracy": _mean(float(r["accuracy"]) for r in rows), "confidence": _mean(float(r["mean_confidence"]) for r in rows), "brier": _mean(float(r["brier"]) for r in rows), "confidence_auc": _mean(float(r["confidence_auc"]) for r in rows if r["confidence_auc"] is not None)})
    _write_csv(output_dir / "learnability_curves.csv", curve_rows)
    reliability: list[dict[str, Any]] = []
    for key, rows in sorted(groups.items()):
        answers = [row.get("parsed_answer") for row in sorted(rows, key=lambda x: int(x["replicate_id"]))]; correctness = [bool(row.get("correct")) for row in rows]; conf = [float(row.get("confidence", 0)) for row in rows]
        reliability.append({"mode": _display_mode(key[0]), "raw_mode": key[0], "world": key[1], "k": key[2], "context_seed": key[3], "probe_id": key[4], "replicates": len(rows), "exact_3way_answer_agreement": float(len(rows) == 3 and len(set(answers)) == 1), "pairwise_answer_agreement": _pairwise_agreement(answers), "exact_3way_correctness_agreement": float(len(rows) == 3 and len(set(correctness)) == 1), "pairwise_correctness_agreement": _pairwise_agreement(correctness), "confidence_variance": statistics.pvariance(conf) if len(conf) > 1 else 0.0, "pairwise_confidence_difference": _mean(abs(conf[i] - conf[j]) for i in range(len(conf)) for j in range(i + 1, len(conf))), "answers": json.dumps(answers)})
    _write_csv(output_dir / "replicate_reliability.csv", reliability)
    _write_csv(output_dir / "anchoring_by_context.csv", summary_rows)
    _svg_line(output_dir / "figures/accuracy_by_k.svg", {mode: [(float(r["k"]), float(r["accuracy"])) for r in curve_rows if r["mode"] == mode] for mode in sorted({r["mode"] for r in curve_rows})}, "Memory learnability calibration", "accuracy")
    _svg_line(output_dir / "figures/confidence_by_k.svg", {mode: [(float(r["k"]), float(r["confidence"])) for r in curve_rows if r["mode"] == mode] for mode in sorted({r["mode"] for r in curve_rows})}, "Confidence calibration", "mean confidence")
    positive = _manual_positive_control(summary_rows); _write_json(output_dir / "synthetic_positive_control.json", positive)
    usage = [float(e.get("observed_cost_usd", 0.0)) for e in completions]
    report = {"protocol": manifest.get("protocol"), "status": "CALIBRATION COMPLETE — OFFLINE ANALYSIS ONLY", "planned_logical_queries": manifest.get("planned_logical_queries"), "completed_logical_queries": manifest.get("completed_logical_queries"), "physical_attempts": manifest.get("physical_attempts"), "observed_cost_usd": manifest.get("observed_cost_usd"), "usage_sum_from_events": sum(usage), "provider_fingerprints": sorted({str((e.get("provider_metadata") or {}).get("system_fingerprint")) for e in completions}), "contexts": len(summary_rows), "positive_control": positive, "generated_at_utc": datetime.now(UTC).isoformat(), "scientific_status": "LEARNABILITY/MEASUREMENT CALIBRATION; NOT EVIDENCE OF EMERGENT SPECIALIZATION"}
    _write_json(output_dir / "calibration_summary.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline memory-learnability report")
    parser.add_argument("--input", default=str(DEFAULT_INPUT)); parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(); print(json.dumps(generate(args.input, args.output), indent=2, sort_keys=True))


if __name__ == "__main__": main()
