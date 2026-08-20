"""Offline audit of hidden ecology-regime observability.

This module never imports a provider or credential path.  It replays the frozen
V2 manifest and journal, computes exact Bayes oracles under three information
sets (hidden regime, pairwise relation, and privileged full regime), and audits
model-prompt aliasing.  It is deliberately analysis-only.
"""

from __future__ import annotations

import argparse
import collections
import csv
import itertools
import json
import math
import statistics
from pathlib import Path
from typing import Any

import numpy as np

from . import observable_learner_calibration_v2 as v2
from .ecological_information import BALANCED_MAPS, FAMILIES, GEOMETRIES, V3Case, generate_environment, posterior_predictive

ROOT = Path(__file__).resolve().parents[2]
REPORT_ROOT = ROOT / "reports/task-ecology/ecology-regime-observability-v1"
V2_REPORT_ROOT = ROOT / "reports/task-ecology/observable-learner-calibration-v2"
V2_DATA_ROOT = ROOT / "data/auto-research/observable-learner-calibration-v2"
RELATION_LABELS = ("SAME_POLICY", "INDEPENDENT_POLICY")
PRIOR_G = {g: 1.0 / 3.0 for g in GEOMETRIES}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def relation_for(geometry: str, source: str | None, target: str) -> str | None:
    if source is None:
        return None
    groups = {"GLOBAL": {f: 0 for f in FAMILIES},
              "BLOCK": {"ACCESS": 0, "RELEASE": 0, "INCIDENT": 1, "PROVENANCE": 1},
              "DIAGONAL": {f: i for i, f in enumerate(FAMILIES)}}[geometry]
    return "SAME_POLICY" if groups[source] == groups[target] else "INDEPENDENT_POLICY"


def _history_likelihood(geometry: str, source: str, history: list[V3Case]) -> float:
    """Likelihood of one source history under the uniform balanced-map prior."""
    # A single source only constrains the policy group containing that source.
    # Every geometry gives that group the same three independent balanced-map
    # priors, so this value is an exact check of source-history regime invariance.
    likelihood = 1.0
    for bit in range(3):
        consistent = [m for m in BALANCED_MAPS if all(m[c.x[bit]] == c.y[bit] for c in history)]
        likelihood *= len(consistent) / len(BALANCED_MAPS)
    return likelihood


def history_regime_posterior(history: list[V3Case], source: str) -> dict[str, float]:
    weights = {g: PRIOR_G[g] * _history_likelihood(g, source, history) for g in GEOMETRIES}
    normalizer = sum(weights.values())
    return {g: weights[g] / normalizer for g in GEOMETRIES} if normalizer else dict(PRIOR_G)


def _mixture_predictive(weights: dict[str, float], source: str, target: str,
                        history: list[V3Case], x: tuple[int, int, int]) -> tuple[float, ...]:
    result = [0.0] * 8
    for geometry, weight in weights.items():
        posterior = posterior_predictive(generate_environment(geometry, 0), source, target, history, x)
        for index, value in enumerate(posterior):
            result[index] += weight * value
    return tuple(result)


def _relation_weights(source: str, target: str, relation: str) -> dict[str, float]:
    weights = {g: PRIOR_G[g] if relation_for(g, source, target) == relation else 0.0 for g in GEOMETRIES}
    normalizer = sum(weights.values())
    return {g: weights[g] / normalizer for g in GEOMETRIES} if normalizer else dict(PRIOR_G)


def oracle_posterior(task: dict[str, Any], mode: str) -> tuple[tuple[float, ...], dict[str, float]]:
    if task["condition"] == "baseline":
        return (tuple([1.0 / 8.0] * 8), dict(PRIOR_G))
    history = [V3Case(item["family"], tuple(item["x"]), tuple(item["y"])) for item in task["memory"]]
    source, target = task["source"], task["target"]
    x = tuple(task["probe"]["x"])
    if mode == "hidden":
        weights = history_regime_posterior(history, source)
    elif mode == "relation":
        relation = relation_for(task["geometry"], source, target)
        weights = _relation_weights(source, target, relation or "INDEPENDENT_POLICY")
    elif mode == "full":
        weights = {g: 1.0 if g == task["geometry"] else 0.0 for g in GEOMETRIES}
    else:
        raise ValueError(mode)
    return _mixture_predictive(weights, source, target, history, x), weights


def posterior_summary(probs: tuple[float, ...], truth: tuple[int, int, int]) -> dict[str, Any]:
    labels = list(itertools.product((0, 1), repeat=3)); maximum = max(probs)
    map_indices = [i for i, value in enumerate(probs) if abs(value - maximum) <= 1e-12]
    return {"A_star": maximum, "p_true": probs[labels.index(truth)],
            "entropy": -sum(p * math.log2(p) for p in probs if p > 0),
            "map_tie_count": len(map_indices), "true_in_map": labels.index(truth) in map_indices,
            "posterior": list(probs)}


def build_oracle_rows(manifest: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    rows_by_mode: dict[str, list[dict[str, Any]]] = {mode: [] for mode in ("hidden", "relation", "full")}
    for task in manifest["tasks"]:
        truth = tuple(task["probe"]["y"])
        for mode in rows_by_mode:
            probs, weights = oracle_posterior(task, mode)
            summary = posterior_summary(probs, truth)
            rows_by_mode[mode].append({"geometry": task["geometry"], "seed": task["seed"],
                "condition": task["condition"], "source": task["source"] or "", "target": task["target"],
                "probe_id": task["probe"]["case_id"], "x": json.dumps(task["probe"]["x"]),
                "relation": relation_for(task["geometry"], task["source"], task["target"]),
                "A_star": summary["A_star"], "p_true": summary["p_true"],
                "posterior_entropy": summary["entropy"], "map_tie_count": summary["map_tie_count"],
                "true_in_map": summary["true_in_map"], "posterior": json.dumps(summary["posterior"]),
                "p_GLOBAL": weights["GLOBAL"], "p_BLOCK": weights["BLOCK"], "p_DIAGONAL": weights["DIAGONAL"]})
    return rows_by_mode


def prompt_aliasing(manifest: dict[str, Any]) -> dict[str, Any]:
    grouped: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = collections.defaultdict(dict)
    for task in manifest["tasks"]:
        if task["condition"] == "transfer" and task["source"] != task["target"]:
            key = (task["seed"], task["source"], task["target"], tuple(task["probe"]["x"]))
            grouped[key][task["geometry"]] = task
    triples = [value for value in grouped.values() if len(value) == 3]
    rows = []
    for value in triples:
        hashes = {value[g]["prompt_hash"] for g in GEOMETRIES}
        truths = {tuple(value[g]["probe"]["y"]) for g in GEOMETRIES}
        row = {"seed": value["GLOBAL"]["seed"], "source": value["GLOBAL"]["source"],
               "target": value["GLOBAL"]["target"], "x": json.dumps(value["GLOBAL"]["probe"]["x"]),
               "prompt_GLOBAL": value["GLOBAL"]["prompt_hash"], "prompt_BLOCK": value["BLOCK"]["prompt_hash"],
               "prompt_DIAGONAL": value["DIAGONAL"]["prompt_hash"], "identical_all": len(hashes) == 1,
               "truth_GLOBAL": json.dumps(value["GLOBAL"]["probe"]["y"]), "truth_BLOCK": json.dumps(value["BLOCK"]["probe"]["y"]),
               "truth_DIAGONAL": json.dumps(value["DIAGONAL"]["probe"]["y"]), "truth_diff_all": len(truths) > 1}
        rows.append(row)
    pairwise = {}
    for left, right in itertools.combinations(GEOMETRIES, 2):
        same = [row for value in triples for row in [{"prompt_same": value[left]["prompt_hash"] == value[right]["prompt_hash"], "truth_diff": tuple(value[left]["probe"]["y"]) != tuple(value[right]["probe"]["y"])}]]
        pairwise[f"{left}/{right}"] = {"comparisons": len(same), "identical_prompt": sum(r["prompt_same"] for r in same),
                                        "different_truth_given_identical": sum(r["prompt_same"] and r["truth_diff"] for r in same)}
    identical = [row for row in rows if row["identical_all"]]
    return {"rows": rows, "summary": {"cross_domain_triples": len(triples), "identical_all": len(identical),
        "different_truth_identical_all": sum(row["truth_diff_all"] for row in identical),
        "fraction_different_truth_identical_all": (sum(row["truth_diff_all"] for row in identical) / len(identical)) if identical else None,
        "pairwise": pairwise}}


def _load_terminal_events(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    events = v2.v1._load_events(V2_DATA_ROOT / "events.jsonl")
    grouped: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for event in events:
        grouped[event["logical_id"]].append(event)
    terminal = {}
    for task in manifest["tasks"]:
        lid = v2.stable_hash({"protocol": v2.PROTOCOL, "tasks_hash": manifest["tasks_hash"], "task": task})
        values = [event for event in grouped.get(lid, []) if event.get("terminal")]
        if values:
            terminal[lid] = values[-1]
    return terminal


def _deepseek_accuracy_rows(manifest: dict[str, Any], terminal: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for task in manifest["tasks"]:
        lid = v2.stable_hash({"protocol": v2.PROTOCOL, "tasks_hash": manifest["tasks_hash"], "task": task})
        event = terminal[lid]
        rows.append({"geometry": task["geometry"], "seed": task["seed"], "condition": task["condition"],
                     "source": task["source"] or "", "target": task["target"], "probe_id": task["probe"]["case_id"],
                     "prompt_hash": task["prompt_hash"], "truth": tuple(task["probe"]["y"]),
                     "decisions": tuple(event["decisions"]) if event.get("decisions") is not None else None,
                     "correct": int(event.get("correct", False))})
    return rows


def pooled_baseline(manifest: dict[str, Any], response_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    baselines = [row for row in response_rows if row["condition"] == "baseline"]
    transfers = [row for row in response_rows if row["condition"] == "transfer"]
    base_index = {(row["geometry"], row["seed"], row["target"], row["probe_id"]): row for row in baselines}
    by_prompt: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in baselines:
        by_prompt[row["prompt_hash"]].append(row)
    fallback = {(row["geometry"], row["seed"], row["target"], row["probe_id"]): row["correct"] for row in baselines}
    pooled_rows = []
    for row in transfers:
        baseline_row = base_index[(row["geometry"], row["seed"], row["target"], row["probe_id"])]
        matched = by_prompt[baseline_row["prompt_hash"]]
        if matched:
            pooled_acc = statistics.mean(int(other["decisions"] == row["truth"]) for other in matched)
        else:
            pooled_acc = float(fallback[(row["geometry"], row["seed"], row["target"], row["probe_id"])])
        pooled_rows.append({**row, "baseline_prompt_hash": baseline_row["prompt_hash"], "pooled_baseline_accuracy": pooled_acc,
                           "pooled_L_DS": row["correct"] - pooled_acc, "pooled_baseline_n": len(matched)})
    return pooled_rows


def _matrix_metrics(rows: list[dict[str, Any]], value_key: str) -> list[dict[str, Any]]:
    output = []
    for geometry in GEOMETRIES:
        cell_values: dict[tuple[str, str], list[float]] = collections.defaultdict(list)
        for row in rows:
            if row["geometry"] == geometry:
                cell_values[(row["source"], row["target"])].append(float(row[value_key]))
        values = {cell: statistics.mean(numbers) for cell, numbers in cell_values.items()}
        diag = statistics.mean(values[(f, f)] for f in FAMILIES)
        off = statistics.mean(values[(s, t)] for s in FAMILIES for t in FAMILIES if s != t)
        within_values = [values[(s, t)] for s, t in (("ACCESS", "RELEASE"), ("RELEASE", "ACCESS"), ("INCIDENT", "PROVENANCE"), ("PROVENANCE", "INCIDENT"))]
        cross_values = [values[(s, t)] for s in FAMILIES for t in FAMILIES if s != t and relation_for(geometry, s, t) == "INDEPENDENT_POLICY"]
        within = statistics.mean(within_values) if within_values else 0.0
        cross = statistics.mean(cross_values) if cross_values else 0.0
        output.append({"geometry": geometry, "D": diag, "O": off, "Q": diag - off, "W": within, "C": cross, "B": within - cross})
    return output


def _svg_bar(path: Path, values: list[tuple[str, float]], title: str) -> None:
    width, height = 760, 300; maximum = max([abs(v) for _, v in values] or [1.0]); baseline = 220
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"><style>text{{font-family:Arial;fill:#222}}</style><text x="20" y="28" font-size="18" font-weight="bold">{title}</text><line x1="30" y1="{baseline}" x2="730" y2="{baseline}" stroke="#555"/>']
    for i, (label, value) in enumerate(values):
        x = 55 + i * 110; h = 150 * abs(value) / maximum; y = baseline - h if value >= 0 else baseline
        color = "#3b82f6" if value >= 0 else "#ef4444"
        parts.append(f'<rect x="{x}" y="{y}" width="70" height="{h}" fill="{color}"/><text x="{x+35}" y="245" text-anchor="middle" font-size="11">{label}</text><text x="{x+35}" y="{y-6 if value>=0 else baseline+h+16}" text-anchor="middle" font-size="11">{value:.3f}</text>')
    parts.append('</svg>'); path.write_text(''.join(parts), encoding='utf-8')


def analyze() -> dict[str, Any]:
    manifest = json.loads((V2_REPORT_ROOT / "manifest.json").read_text(encoding="utf-8"))
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    oracle_rows = build_oracle_rows(manifest)
    for mode, rows in oracle_rows.items():
        write_csv(REPORT_ROOT / f"bayes_{mode}_prompt_level.csv", rows)
    aliases = prompt_aliasing(manifest); write_csv(REPORT_ROOT / "prompt_aliasing.csv", aliases["rows"])
    (REPORT_ROOT / "prompt_aliasing_summary.json").write_text(json.dumps(aliases["summary"], indent=2), encoding="utf-8")
    terminal = _load_terminal_events(manifest); response_rows = _deepseek_accuracy_rows(manifest, terminal)
    baseline = [row for row in response_rows if row["condition"] == "baseline"]
    base_by_key = {(row["geometry"], row["seed"], row["target"], row["probe_id"]): row for row in baseline}
    comparison_rows = []
    for task in manifest["tasks"]:
        if task["condition"] != "transfer": continue
        key = (task["geometry"], task["seed"], task["target"], task["probe"]["case_id"])
        ds = next(row for row in response_rows if row["geometry"] == task["geometry"] and row["seed"] == task["seed"] and row["condition"] == "transfer" and row["source"] == task["source"] and row["target"] == task["target"] and row["probe_id"] == task["probe"]["case_id"])
        b = base_by_key[key]
        comparison_rows.append({**ds, "baseline_correct": b["correct"], "L_DS": ds["correct"] - b["correct"],
                                **{f"A_star_{mode}": next(row for row in oracle_rows[mode] if row["geometry"] == task["geometry"] and row["seed"] == task["seed"] and row["condition"] == "transfer" and row["source"] == task["source"] and row["target"] == task["target"] and row["probe_id"] == task["probe"]["case_id"])["A_star"] for mode in ("hidden", "relation", "full")}})
    oracle_comparison = []
    for mode in ("hidden", "relation", "full"):
        value_rows = []
        for row in oracle_rows[mode]:
            if row["condition"] != "transfer": continue
            value_rows.append({"geometry": row["geometry"], "source": row["source"], "target": row["target"], "value": row["A_star"] - 0.125})
        for metric in _matrix_metrics(value_rows, "value"):
            oracle_comparison.append({"oracle": mode, **metric})
    ds_metrics = _matrix_metrics(comparison_rows, "L_DS")
    for metric in ds_metrics: oracle_comparison.append({"oracle": "DeepSeek", **metric})
    write_csv(REPORT_ROOT / "oracle_comparison.csv", oracle_comparison)
    for mode in ("hidden", "relation", "full"):
        rows = [{"geometry": r["geometry"], "source": r["source"], "target": r["target"], "L_star": r["A_star"] - 0.125}
                for r in oracle_rows[mode] if r["condition"] == "transfer"]
        write_csv(REPORT_ROOT / f"{mode}_geometry_metrics.csv", [{"oracle": mode, **metric} for metric in _matrix_metrics(rows, "L_star")])
    pooled = pooled_baseline(manifest, response_rows); write_csv(REPORT_ROOT / "pooled_baseline_analysis.csv", pooled)
    pooled_metrics = _matrix_metrics(pooled, "pooled_L_DS")
    original_metrics = _matrix_metrics(comparison_rows, "L_DS")
    pooled_summary = {"original": original_metrics, "pooled": pooled_metrics,
                      "baseline_prompt_groups": len({r["prompt_hash"] for r in baseline}),
                      "baseline_rows": len(baseline)}
    (REPORT_ROOT / "pooled_baseline_summary.json").write_text(json.dumps(pooled_summary, indent=2), encoding="utf-8")
    heuristic_rows = []
    for metric in ds_metrics:
        diag = metric["D"]
        heuristic_rows.append({"geometry": metric["geometry"], "heuristic": "SAME-FAMILY-GATED", "D": diag, "O": 0.0, "Q": diag, "B": diag})
        heuristic_rows.append({"geometry": metric["geometry"], "heuristic": "OBSERVED-DEEPSEEK", "D": metric["D"], "O": metric["O"], "Q": metric["Q"], "B": metric["B"]})
    write_csv(REPORT_ROOT / "learner_prior_heuristics.csv", heuristic_rows)
    figures = REPORT_ROOT / "figures"; figures.mkdir(parents=True, exist_ok=True)
    for mode in ("hidden", "relation", "full"):
        for geometry in GEOMETRIES:
            rows = [r for r in oracle_rows[mode] if r["condition"] == "transfer" and r["geometry"] == geometry]
            # mean over seed/probe for each source-target cell
            values = {(s, t): statistics.mean(float(r["A_star"]) - 0.125 for r in rows if r["source"] == s and r["target"] == t) for s in FAMILIES for t in FAMILIES}
            matrix = np.array([[values[(s, t)] for t in FAMILIES] for s in FAMILIES], dtype=float)
            v2.v1._svg_heatmap(figures / f"Lstar_{mode}_{geometry.lower()}.svg", matrix, f"L* {mode} {geometry}")
    _svg_bar(figures / "prompt_aliasing.svg", [("identical", aliases["summary"]["identical_all"]), ("diff truth", aliases["summary"]["different_truth_identical_all"])], "Identical prompt aliases")
    technical = json.loads((V2_REPORT_ROOT / "technical_health.json").read_text(encoding="utf-8")) if (V2_REPORT_ROOT / "technical_health.json").exists() else {}
    summary = {"protocol": "ECOLOGY-REGIME-OBSERVABILITY-V1", "external_model_calls": 0, "external_spend_usd": 0.0,
               "prompt_aliasing": aliases["summary"], "same_history_regime_posterior": history_regime_posterior([V3Case("ACCESS", (0, 0, 0), (0, 0, 0))], "ACCESS"),
               "sharing_probabilities": {"same_family": 1.0, "canonical_block_pair": 2.0/3.0, "other_cross_family": 1.0/3.0},
               "deepseek_metrics": ds_metrics, "pooled_metrics": pooled_metrics, "technical_health": technical}
    (REPORT_ROOT / "audit_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline ecology regime observability audit; never calls a model")
    parser.add_argument("--run", action="store_true", help="run the offline audit")
    args = parser.parse_args()
    if not args.run:
        parser.error("use --run; external inference is not supported")
    print(json.dumps(analyze(), indent=2, default=float))


if __name__ == "__main__":
    main()
