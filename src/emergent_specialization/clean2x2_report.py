"""Offline report generator for the completed clean v2 2x2 campaign.

The generator reads only the immutable campaign manifest and run artifacts.  It
does not call a provider and does not change any experiment state.  Outputs are
deliberately tidy and machine-readable so later statistical analyses can be
performed without rerunning or reinterpreting the raw JSONL.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from .analysis import (
    checkpoint_rows,
    competence_rows,
    hse_trajectory_rows,
    load_run,
    round_rows,
    routing_rows,
    usage_summary,
)
from .health import run_health
from .metrics.information import mi_null_diagnostic
from .metrics.online import online_observables, online_team_accuracy


ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = ROOT / "data" / "campaigns" / "developmental-dynamics-v2" / "campaign.json"


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("\n", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def _svg_line_plot(path: Path, series: dict[str, list[tuple[float, float]]], *, title: str, y_label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 960, 520
    left, right, top, bottom = 82, 28, 62, 58
    all_points = [point for values in series.values() for point in values]
    xs = [point[0] for point in all_points] or [0, 1]
    ys = [point[1] for point in all_points] or [0, 1]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    if ymax <= ymin:
        ymax = ymin + 1.0
    def x(value: float) -> float:
        return left + (value - xmin) / max(1e-12, xmax - xmin) * (width - left - right)
    def y(value: float) -> float:
        return height - bottom - (value - ymin) / (ymax - ymin) * (height - top - bottom)
    colors = {"confidence/private": "#1f6f8b", "confidence/shared": "#d95f59", "random/private": "#4c956c", "random/shared": "#8c6bb1"}
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="#fffdf8"/>']
    parts.append(f'<text x="{left}" y="34" font-family="sans-serif" font-size="22" font-weight="700">{title}</text>')
    parts.append(f'<text x="18" y="{height/2}" transform="rotate(-90 18 {height/2})" font-family="sans-serif" font-size="14">{y_label}</text>')
    parts.append(f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#333"/>')
    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#333"/>')
    for label, values in series.items():
        points = " ".join(f"{x(a):.1f},{y(b):.1f}" for a, b in values)
        color = colors.get(label, "#333")
        parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{points}"/>')
        for a, b in values:
            parts.append(f'<circle cx="{x(a):.1f}" cy="{y(b):.1f}" r="3.5" fill="{color}"/>')
    legend_x = left
    for label in series:
        color = colors.get(label, "#333")
        parts.append(f'<line x1="{legend_x}" y1="{height-22}" x2="{legend_x+22}" y2="{height-22}" stroke="{color}" stroke-width="4"/>')
        parts.append(f'<text x="{legend_x+28}" y="{height-17}" font-family="sans-serif" font-size="13">{label}</text>')
        legend_x += 190
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _svg_heatmap(path: Path, matrix: dict[str, dict[str, float]], *, title: str, value_label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    agents = sorted({agent for row in matrix.values() for agent in row})
    worlds = sorted(matrix)
    width, height = 760, 420
    left, top, cell_w, cell_h = 150, 90, 120, 58
    values = [float(matrix[w].get(a, 0.0)) for w in worlds for a in agents]
    lo, hi = min(values or [0.0]), max(values or [1.0])
    if hi <= lo:
        hi = lo + 1.0
    def color(v: float) -> str:
        t = (v - lo) / (hi - lo)
        r = int(246 - 150 * t); g = int(238 - 100 * t); b = int(220 - 20 * t)
        return f"#{r:02x}{g:02x}{b:02x}"
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="#fffdf8"/>']
    parts.append(f'<text x="24" y="38" font-family="sans-serif" font-size="22" font-weight="700">{title}</text>')
    parts.append(f'<text x="24" y="62" font-family="sans-serif" font-size="13">{value_label}; rows = worlds, columns = agents</text>')
    for j, agent in enumerate(agents):
        parts.append(f'<text x="{left+j*cell_w+cell_w/2}" y="82" text-anchor="middle" font-family="sans-serif" font-size="14">{agent}</text>')
    for i, world in enumerate(worlds):
        parts.append(f'<text x="{left-12}" y="{top+i*cell_h+cell_h/2+5}" text-anchor="end" font-family="sans-serif" font-size="14">{world}</text>')
        for j, agent in enumerate(agents):
            value = float(matrix[world].get(agent, 0.0))
            xx, yy = left+j*cell_w, top+i*cell_h
            parts.append(f'<rect x="{xx}" y="{yy}" width="{cell_w-4}" height="{cell_h-4}" rx="5" fill="{color(value)}" stroke="#fff"/>')
            parts.append(f'<text x="{xx+cell_w/2-2}" y="{yy+cell_h/2+5}" text-anchor="middle" font-family="sans-serif" font-size="16">{value:.3f}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def generate(campaign_path: str | Path = CAMPAIGN, output_dir: str | Path | None = None) -> dict[str, Any]:
    campaign_path = Path(campaign_path).resolve()
    manifest = json.loads(campaign_path.read_text(encoding="utf-8"))
    output = Path(output_dir).resolve() if output_dir else ROOT / "reports" / "campaigns" / "developmental-dynamics-v2" / "clean-2x2"
    output.mkdir(parents=True, exist_ok=True)
    bundles = []
    inventory: list[dict[str, Any]] = []
    all_checkpoint: list[dict[str, Any]] = []
    all_tidy: list[dict[str, Any]] = []
    all_comp: list[dict[str, Any]] = []
    all_route: list[dict[str, Any]] = []
    all_round: list[dict[str, Any]] = []
    all_online: list[dict[str, Any]] = []
    cell_checkpoints: dict[tuple[str, str, int], dict[str, Any]] = {}
    for planned in manifest["runs"]:
        run_dir = Path(planned["run_dir"]).resolve()
        bundle = load_run(run_dir)
        health = run_health(run_dir)
        config = bundle.metadata.get("config", {})
        router = str((config.get("router") or {}).get("strategy", planned.get("router")))
        cell = f"{router}/{bundle.condition}"
        bundles.append(bundle)
        usage = usage_summary(bundle)
        inventory.append({
            "run_id": bundle.run_id, "stage": "clean-v2", "cell": cell, "router": router,
            "condition": bundle.condition, "seed": bundle.seed, "run_dir": str(run_dir),
            "status": bundle.summary.get("status"), "health": health["health_classification"],
            "expected_logical_completions": health["expected_logical_completions"],
            "successful_logical_completions": health["successful_logical_completions"],
            "physical_attempts": health["physical_attempts"], "retries": health["retries"],
            "timeout_count": health["timeout_count"], "parse_error_count": health["parse_error_count"],
            "empty_content_count": health["empty_content_count"], "semantic_ood_count": health["semantic_answer_domain_violation_count"],
            "completion_coverage": health["completion_coverage"], "usage_coverage": health["usage_coverage"],
            "observed_cost_usd": health["observed_cost_usd"], "reported_usage_status": usage.get("status"),
            "system_fingerprints": ";".join(sorted({str((e.get("provider_metadata") or {}).get("system_fingerprint")) for e in bundle.events_of_type("inference") if (e.get("provider_metadata") or {}).get("system_fingerprint")})),
            "git_commit": bundle.metadata.get("git_commit"), "config_hash": planned.get("config_hash"),
            "probe_set_hash": planned.get("probe_set_hash"), "protocol_version": planned.get("protocol_version"),
        })
        rounds = round_rows(bundle)
        all_round.extend([{**row, "router": router, "cell": cell} for row in rounds])
        online = online_observables(bundle.events, num_agents=len(bundle.agent_ids), mi_permutations=200, mi_min_samples=8, mi_seed=0)
        all_online.extend([{**row, "router": router, "cell": cell} for row in online])
        baseline_phi = None
        baseline_hse = None
        for row in checkpoint_rows(bundle):
            checkpoint = int(row["checkpoint"])
            if checkpoint == 0:
                baseline_phi, baseline_hse = row.get("phi"), row.get("normalized_hse")
            row = {**row, "router": router, "cell": cell, "git_commit": bundle.metadata.get("git_commit"), "health": health["health_classification"]}
            row["delta_phi"] = row.get("phi") - baseline_phi if isinstance(row.get("phi"), (int, float)) and isinstance(baseline_phi, (int, float)) else None
            row["delta_normalized_hse"] = row.get("normalized_hse") - baseline_hse if isinstance(row.get("normalized_hse"), (int, float)) and isinstance(baseline_hse, (int, float)) else None
            prefix = [r for r in rounds if r["round"] <= checkpoint]
            mi = mi_null_diagnostic([str(r["world"]) for r in prefix], [str(r["selected_agent"]) for r in prefix], permutations=200, seed=0) if len(prefix) >= 2 else {"observed_mi": 0.0, "normalized_observed_mi": 0.0, "null_mean": None, "normalized_null_mean": None, "normalized_excess_mi": None, "null_percentile": None, "permutations": 0, "seed": 0}
            for key, value in mi.items(): row[f"online_{key}"] = value
            online_prefix = [r for r in online if int(r["round"]) == checkpoint]
            if online_prefix:
                row["online_interaction_accuracy"] = online_prefix[-1].get("online_interaction_accuracy")
            else:
                row["online_interaction_accuracy"] = None
            all_checkpoint.append(row)
            for metric, value in row.items():
                if metric in {"run_id", "condition", "seed", "checkpoint", "router", "cell", "git_commit", "health", "competence_differentiation_eigenvalues"}:
                    continue
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    all_tidy.append({"campaign": manifest["campaign"], "stage": "clean-v2", "cell": cell, "condition": bundle.condition, "router": router, "seed": bundle.seed, "checkpoint": checkpoint, "run_id": bundle.run_id, "git_commit": bundle.metadata.get("git_commit"), "health": health["health_classification"], "metric_name": metric, "metric_value": value})
            cell_checkpoints[(cell, bundle.run_id, checkpoint)] = row
        all_comp.extend([{**row, "router": router, "cell": cell, "health": health["health_classification"]} for row in competence_rows(bundle)])
        all_route.extend([{**row, "router": router, "cell": cell, "health": health["health_classification"]} for row in routing_rows(bundle)])
    _write_csv(output / "run_inventory.csv", inventory)
    _write_csv(output / "checkpoint_metrics.csv", all_checkpoint)
    _write_csv(output / "tidy_metrics.csv", all_tidy)
    _write_csv(output / "competence_long.csv", all_comp)
    _write_csv(output / "routing_long.csv", all_route)
    _write_csv(output / "online_rounds.csv", all_round)
    _write_csv(output / "online_observables.csv", all_online)

    health_counts = Counter(row["health"] for row in inventory)
    error_totals = {key: sum(int(row[key]) for row in inventory) for key in ("retries", "timeout_count", "parse_error_count", "empty_content_count", "semantic_ood_count")}
    by_cell: dict[str, dict[str, Any]] = {}
    for cell in sorted({row["cell"] for row in inventory}):
        rows = [row for row in inventory if row["cell"] == cell]
        metrics = [row for row in all_checkpoint if row["cell"] == cell and int(row["checkpoint"]) == 20]
        by_cell[cell] = {"runs": len(rows), "seeds": sorted(row["seed"] for row in rows), "health": dict(Counter(row["health"] for row in rows)), "mean_final": {name: _mean([float(m[name]) for m in metrics if isinstance(m.get(name), (int, float))]) for name in ("normalized_hse", "phi", "normalized_task_agent_mutual_information", "normalized_utilization_entropy", "oracle_gain", "best_individual_accuracy", "oracle_society_accuracy", "routing_alignment_eta", "delta_match")}}
    summary = {
        "generated_at_utc": datetime.now(UTC).isoformat(), "campaign": manifest["campaign"], "protocol_version": manifest["protocol_version"],
        "scientific_status": "DESCRIPTIVE AGGREGATE ONLY — NOT A CAUSAL OR CONFIRMATORY CONCLUSION",
        "runs": len(inventory), "expected_runs": 40, "logical_completions": sum(int(row["successful_logical_completions"]) for row in inventory), "expected_logical_completions": sum(int(row["expected_logical_completions"]) for row in inventory), "physical_attempts": sum(int(row["physical_attempts"]) for row in inventory), "observed_cost_usd": sum(float(row["observed_cost_usd"] or 0.0) for row in inventory), "health_counts": dict(health_counts), "error_totals": error_totals, "by_cell": by_cell, "probe_set_hashes": sorted({row["probe_set_hash"] for row in inventory}), "git_commits": sorted({str(row["git_commit"]) for row in inventory}),
    }
    _write_json(output / "clean_2x2_summary.json", summary)

    for cell in sorted(by_cell):
        final = [row for row in all_checkpoint if row["cell"] == cell and int(row["checkpoint"]) == 20]
        for field, filename, title in (("normalized_hse", "hse-final-heatmap.svg", "Final normalized HSE by run"), ("phi", "phi-final-heatmap.svg", "Final competence differentiation Phi by run")):
            matrix = {str(row["seed"]): {field: float(row[field]) if isinstance(row.get(field), (int, float)) else 0.0} for row in final}
            # Encode a one-column run heatmap; the cell-specific scalar summary is in CSV.
            _svg_heatmap(output / "figures" / f"{cell.replace('/', '-')}-{filename}", matrix, title=f"{cell}: {title}", value_label=field)
        competence = defaultdict(list)
        routed = defaultdict(list)
        for row in all_comp:
            if row["cell"] == cell and int(row["checkpoint"]) == 20:
                competence[(str(row["world"]), str(row["agent_id"]))].append(float(row["accuracy"]))
        for row in all_route:
            if row["cell"] == cell and int(row["checkpoint"]) == 20:
                routed[(str(row["world"]), str(row["agent_id"]))].append(float(row["proportion"]))
        worlds = sorted({key[0] for key in competence} | {key[0] for key in routed})
        agents = sorted({key[1] for key in competence} | {key[1] for key in routed})
        competence_matrix = {world: {agent: _mean(competence.get((world, agent), [])) or 0.0 for agent in agents} for world in worlds}
        routing_matrix = {world: {agent: _mean(routed.get((world, agent), [])) or 0.0 for agent in agents} for world in worlds}
        _svg_heatmap(output / "figures" / f"{cell.replace('/', '-')}-competence-checkpoint20.svg", competence_matrix, title=f"{cell}: mean competence matrix at checkpoint 20", value_label="accuracy")
        _svg_heatmap(output / "figures" / f"{cell.replace('/', '-')}-routing-checkpoint20.svg", routing_matrix, title=f"{cell}: mean routing matrix at checkpoint 20", value_label="routing proportion")
    for field, filename, title in (("normalized_hse", "normalized-hse-trajectory.svg", "Mean normalized HSE across checkpoints"), ("phi", "phi-trajectory.svg", "Mean competence differentiation Phi across checkpoints")):
        series: dict[str, list[tuple[float, float]]] = {}
        for cell in sorted(by_cell):
            values = []
            for checkpoint in (0, 10, 20):
                rows = [r for r in all_checkpoint if r["cell"] == cell and int(r["checkpoint"]) == checkpoint and isinstance(r.get(field), (int, float))]
                if rows: values.append((checkpoint, statistics.fmean(float(r[field]) for r in rows)))
            series[cell] = values
        _svg_line_plot(output / "figures" / filename, series, title=title, y_label=field)

    md = ["# Clean v2 2×2 campaign report", "", "**Status:** descriptive aggregate only; this document does not make a causal or confirmatory claim.", "", "## Design and provenance", "", f"- Campaign: `{manifest['campaign']}`", f"- Protocol: `{manifest['protocol_version']}`", "- Provider: DeepSeek Direct; model: `deepseek-v4-flash`; credential source: macOS Keychain", "- Cells: confidence/private, confidence/shared, random/private, random/shared", "- Seeds: 1–10 per cell; 4 agents; 20 rounds; checkpoints 0/10/20; 40 probes/checkpoint", f"- Probe-set hashes observed: `{', '.join(summary['probe_set_hashes'])}`", f"- Git commits observed in artifacts: `{', '.join(summary['git_commits'])}`", "", "## Infrastructure health", "", f"- Runs: {summary['runs']}/{summary['expected_runs']}", f"- Logical completion coverage: {summary['logical_completions']}/{summary['expected_logical_completions']}", f"- Physical attempts: {summary['physical_attempts']}", f"- Observed cost: `${summary['observed_cost_usd']:.6f}`", f"- Health counts: `{json.dumps(summary['health_counts'], sort_keys=True)}`", f"- Retry/error totals: `{json.dumps(summary['error_totals'], sort_keys=True)}`", "", "`HEALTHY / RECOVERED` means complete logical coverage with at least one recovered attempt or incomplete usage metadata; it is included but flagged. Semantic out-of-domain answers are scientific model outputs, not parse failures.", "", "## Cell-level descriptive endpoints", "", "| Cell | Runs | HSE20 | Phi20 | normalized MI20 | Utilization20 | Oracle gain20 | Eta route20 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for cell, values in by_cell.items():
        m = values["mean_final"]
        fmt = lambda value: "n/a" if value is None else f"{value:.4f}"
        md.append(f"| {cell} | {values['runs']} | {fmt(m['normalized_hse'])} | {fmt(m['phi'])} | {fmt(m['normalized_task_agent_mutual_information'])} | {fmt(m['normalized_utilization_entropy'])} | {fmt(m['oracle_gain'])} | {fmt(m['routing_alignment_eta'])} |")
    md += ["", "## Interpretation guardrails", "", "- HSE is behavioral diversity, not specialization.", "- Phi measures competence differentiation, not useful roles.", "- MI and routing concentration describe organization and can also indicate collapse.", "- Oracle gain and matching gain describe complementarity potential, not realized division of labor.", "- Random-routing cells are an analysis control for confidence-driven selection; no result is labeled a causal effect here.", "- The old v1 artifacts are legacy/exploratory and are not mixed into this clean v2 aggregate.", "", "## Files", "", "- `run_inventory.csv`: one row per selected manifest run.", "- `checkpoint_metrics.csv`: one row per run/checkpoint.", "- `tidy_metrics.csv`: long-format metric table.", "- `competence_long.csv`, `routing_long.csv`: heatmap-ready matrices.", "- `online_observables.csv`, `online_rounds.csv`: cheap online trajectories.", "- `figures/`: SVG trajectories and endpoint heatmaps."]
    (output / "CLEAN_2X2_REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return summary


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate the clean v2 2x2 report offline")
    parser.add_argument("--campaign", default=str(CAMPAIGN))
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)
    print(json.dumps(generate(args.campaign, args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
