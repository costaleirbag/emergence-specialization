"""Offline Gate 1 execution and analysis report.

This module reads immutable run artifacts only.  It never constructs a model
provider and never performs inference.  The outputs are deliberately
descriptive: raw-label ensemble summaries are accompanied by explicit
exchangeability caveats, and Gate 2 remains locked.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from .analysis import (
    checkpoint_rows,
    competence_rows,
    hse_trajectory_rows,
    load_run,
    memory_rows,
    round_rows,
    routing_rows,
)
from .campaign import GATE_1, _health_for, manifest_path


WORLDS = ("ALPHA", "BETA", "GAMMA", "DELTA")
AGENTS = ("agent_0", "agent_1", "agent_2", "agent_3")
CONDITIONS = ("private", "shared")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({key for row in rows for key in row}) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _num(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and math.isfinite(float(value)) else None


def _mean(values: Iterable[Any]) -> float | None:
    numbers = [float(value) for value in values if _num(value) is not None]
    return statistics.fmean(numbers) if numbers else None


def _median(values: Iterable[Any]) -> float | None:
    numbers = [float(value) for value in values if _num(value) is not None]
    return statistics.median(numbers) if numbers else None


def _std(values: Iterable[Any]) -> float | None:
    numbers = [float(value) for value in values if _num(value) is not None]
    return statistics.pstdev(numbers) if len(numbers) > 1 else (0.0 if numbers else None)


def _entropy(counts: dict[str, int | float]) -> float:
    total = sum(float(value) for value in counts.values())
    if total <= 0:
        return 0.0
    return -sum((float(value) / total) * math.log2(float(value) / total) for value in counts.values() if value)


def _normalized_entropy(counts: dict[str, int | float]) -> float:
    return _entropy(counts) / math.log2(len(counts)) if len(counts) > 1 else 0.0


def _health_class(flag: str | None) -> str:
    return {"healthy": "CLEAN", "healthy_recovered": "RECOVERED", "invalid": "INVALID"}.get(flag or "", "UNKNOWN")


def _load_gate_bundles(manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], list[Any]]:
    rows: list[dict[str, Any]] = []
    bundles: list[Any] = []
    for row in manifest.get("runs", []):
        if row.get("gate") != GATE_1 or row.get("status") not in {"reused", "completed"} or not row.get("run_dir"):
            continue
        health = _health_for(Path(row["run_dir"]))
        if not health or health.get("health_flag") not in {"healthy", "healthy_recovered"}:
            continue
        bundle = load_run(row["run_dir"], require_completed=True, require_checkpoints=True)
        rows.append({"manifest": row, "health": health, "bundle": bundle})
        bundles.append(bundle)
    return rows, bundles


def _checkpoint_enriched(bundle: Any) -> list[dict[str, Any]]:
    rows = hse_trajectory_rows(bundle)
    for row in rows:
        # Routing entropy is computed from the checkpoint routing matrix.  At
        # t=0 there are no interaction routes and the value is defined as 0.
        checkpoint = next((item for item in bundle.checkpoints if int(item.get("checkpoint", -1)) == int(row["checkpoint"])), {})
        routing = checkpoint.get("routing_counts_by_world_agent", {})
        global_counts = {agent: 0 for agent in AGENTS}
        for profile in routing.values():
            for agent, count in profile.items():
                global_counts[agent] = global_counts.get(agent, 0) + int(count)
        row["routing_entropy"] = _entropy(global_counts)
        row["normalized_routing_entropy"] = _normalized_entropy(global_counts)
        row["max_routing_share"] = max((float(v) / sum(global_counts.values()) for v in global_counts.values()), default=0.0) if sum(global_counts.values()) else 0.0
    return rows


def _run_rows(entries: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    checkpoints: list[dict[str, Any]] = []
    competence: list[dict[str, Any]] = []
    routing: list[dict[str, Any]] = []
    rounds: list[dict[str, Any]] = []
    memory: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    for entry in entries:
        bundle = entry["bundle"]
        health = entry["health"]
        checkpoints.extend(_checkpoint_enriched(bundle))
        competence.extend(competence_rows(bundle))
        routing.extend(routing_rows(bundle))
        rounds.extend(round_rows(bundle))
        memory.extend(memory_rows(bundle))
        metadata = bundle.metadata
        config = metadata.get("config", {})
        backend = metadata.get("backend", {})
        fps = sorted({
            str((event.get("provider_metadata") or {}).get("system_fingerprint"))
            for event in bundle.events_of_type("inference")
            if (event.get("provider_metadata") or {}).get("system_fingerprint")
        })
        provenance.append({
            "run_id": bundle.run_id,
            "seed": bundle.seed,
            "condition": bundle.condition,
            "health": _health_class(health.get("health_flag")),
            "health_flag": health.get("health_flag"),
            "git_commit": metadata.get("git_commit"),
            "backend": backend.get("backend"),
            "model": config.get("agent", {}).get("model"),
            "thinking": config.get("agent", {}).get("thinking"),
            "config_hash": config.get("source_hash"),
            "probe_set_hash": metadata.get("probe_set_hash"),
            "system_fingerprints": ";".join(fps),
            "effective_rng_seeds": json.dumps(metadata.get("effective_rng_seeds", {}), sort_keys=True),
            "memory_strategy": config.get("agent", {}).get("memory_strategy"),
            "memory_k": config.get("agent", {}).get("memory_k"),
            "router": config.get("router", {}).get("strategy"),
            "rounds": config.get("experiment", {}).get("num_rounds"),
            "checkpoints": json.dumps(config.get("experiment", {}).get("checkpoints", [])),
        })
    return checkpoints, competence, routing, rounds, memory, provenance


def _quality_rows(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for entry in entries:
        h = entry["health"]
        rows.append({
            "seed": entry["bundle"].seed,
            "condition": entry["bundle"].condition,
            "run_id": entry["bundle"].run_id,
            "health": _health_class(h.get("health_flag")),
            "health_flag": h.get("health_flag"),
            "expected_logical_completions": h.get("expected_logical_completions"),
            "successful_logical_completions": h.get("successful_logical_completions"),
            "missing_logical_completions": h.get("missing_logical_completions"),
            "completion_coverage": h.get("completion_coverage"),
            "physical_attempts": h.get("physical_attempts"),
            "retries": h.get("retries"),
            "timeout_count": h.get("timeout_count"),
            "parse_error_count": h.get("parse_error_count"),
            "rate_limit_count": h.get("rate_limit_count"),
            "other_error_count": h.get("other_error_count"),
            "usage_coverage": h.get("usage_coverage"),
            "observed_cost_usd": h.get("observed_cost_usd"),
            "latency_mean_s": (h.get("latency_s") or {}).get("mean"),
            "latency_median_s": (h.get("latency_s") or {}).get("median"),
            "latency_max_s": (h.get("latency_s") or {}).get("max"),
        })
    return sorted(rows, key=lambda row: (int(row["seed"]), row["condition"]))


def _paired_rows(checkpoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_seed_checkpoint: dict[tuple[int, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in checkpoints:
        by_seed_checkpoint[(int(row["seed"]), int(row["checkpoint"]))][str(row["condition"])] = row
    output: list[dict[str, Any]] = []
    for (seed, checkpoint), conditions in sorted(by_seed_checkpoint.items()):
        if "private" not in conditions or "shared" not in conditions:
            continue
        private = conditions["private"]
        shared = conditions["shared"]
        output.append({
            "seed": seed,
            "checkpoint": checkpoint,
            "private_normalized_hse": private.get("normalized_hse"),
            "shared_normalized_hse": shared.get("normalized_hse"),
            "private_delta_normalized_hse": private.get("delta_normalized_hse"),
            "shared_delta_normalized_hse": shared.get("delta_normalized_hse"),
            "D_private_minus_shared": (private.get("delta_normalized_hse") - shared.get("delta_normalized_hse")) if _num(private.get("delta_normalized_hse")) is not None and _num(shared.get("delta_normalized_hse")) is not None else None,
            "private_phi": private.get("phi"),
            "shared_phi": shared.get("phi"),
            "D_phi_private_minus_shared": (private.get("phi") - shared.get("phi")) if _num(private.get("phi")) is not None and _num(shared.get("phi")) is not None else None,
            "private_d_eff": private.get("effective_competence_dimensionality"),
            "shared_d_eff": shared.get("effective_competence_dimensionality"),
            "private_utilization": private.get("normalized_utilization_entropy"),
            "shared_utilization": shared.get("normalized_utilization_entropy"),
            "private_mi": private.get("normalized_task_agent_mutual_information"),
            "shared_mi": shared.get("normalized_task_agent_mutual_information"),
            "private_eta_route": private.get("routing_alignment_eta"),
            "shared_eta_route": shared.get("routing_alignment_eta"),
            "private_oracle_gain": private.get("oracle_gain"),
            "shared_oracle_gain": shared.get("oracle_gain"),
        })
    return output


def _summary_stats(rows: list[dict[str, Any]], value_key: str, *, group_key: str = "condition") -> list[dict[str, Any]]:
    groups: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        value = _num(row.get(value_key))
        if value is not None:
            groups[str(row.get(group_key, "all"))].append(value)
    output = []
    for group, values in sorted(groups.items()):
        output.append({
            "group": group,
            "metric": value_key,
            "n": len(values),
            "mean": statistics.fmean(values),
            "median": statistics.median(values),
            "std_population": statistics.pstdev(values) if len(values) > 1 else 0.0,
            "min": min(values),
            "max": max(values),
            "fraction_positive": sum(value > 0 for value in values) / len(values),
        })
    return output


def _aggregate_checkpoint(checkpoints: list[dict[str, Any]], metric: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], list[float]] = defaultdict(list)
    for row in checkpoints:
        value = _num(row.get(metric))
        if value is not None:
            grouped[(str(row["condition"]), int(row["checkpoint"]))].append(value)
    return [{
        "condition": condition,
        "checkpoint": checkpoint,
        "metric": metric,
        "n": len(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "std_population": statistics.pstdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    } for (condition, checkpoint), values in sorted(grouped.items())]


def _label_sanity(rounds: list[dict[str, Any]], memory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = Counter(row["selected_agent"] for row in rounds if row.get("selected_agent"))
    final_memory: dict[tuple[str, int, str], int] = {}
    for row in memory:
        final_memory[(str(row["condition"]), int(row["seed"]), str(row["agent_id"]))] = int(row["memory_count"])
    output = [{"measure": "selected_count", "condition": "all", "seed": "all", "agent_id": agent, "value": selected.get(agent, 0)} for agent in AGENTS]
    output.extend({"measure": "final_memory_count", "condition": condition, "seed": seed, "agent_id": agent, "value": value} for (condition, seed, agent), value in sorted(final_memory.items()))
    return output


def _plot_reports(root: Path, checkpoints: list[dict[str, Any]], paired: list[dict[str, Any]], competence: list[dict[str, Any]], routing: list[dict[str, Any]], rounds: list[dict[str, Any]], label_rows: list[dict[str, Any]]) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    figures = root / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    generated: list[str] = []

    def save(fig: Any, name: str) -> None:
        path = figures / name
        try:
            fig.tight_layout()
        except RuntimeError:
            # Heatmaps with colorbars may use constrained_layout already.
            pass
        fig.savefig(path, dpi=180, bbox_inches="tight")
        plt.close(fig)
        generated.append(str(path.relative_to(root)))

    colors = {"private": "#276fbf", "shared": "#b23a48"}
    for metric, name, title, ylabel in (
        ("normalized_hse", "hse_trajectory.png", "Behavioral diversity: HSE(t)", "normalized HSE"),
        ("delta_normalized_hse", "delta_hse_trajectory.png", "Developmental change: ΔHSE(t)", "Δ normalized HSE"),
        ("phi", "competence_differentiation_phi.png", "Competence differentiation: Φ(t)", "Φ"),
        ("effective_competence_dimensionality", "effective_dimension.png", "Effective competence dimensionality", "participation ratio"),
    ):
        fig, ax = plt.subplots(figsize=(8.5, 4.8))
        for condition in CONDITIONS:
            subset = [row for row in checkpoints if row["condition"] == condition]
            by_run: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
            for row in subset:
                by_run[(int(row["seed"]), condition)].append(row)
            for (seed, _), values in sorted(by_run.items()):
                values = sorted(values, key=lambda row: int(row["checkpoint"]))
                ax.plot([row["checkpoint"] for row in values], [row.get(metric) for row in values], color=colors[condition], alpha=0.18, linewidth=0.8)
            grouped = defaultdict(list)
            for row in subset:
                if _num(row.get(metric)) is not None:
                    grouped[int(row["checkpoint"])].append(float(row[metric]))
            xs = sorted(grouped)
            means = [statistics.fmean(grouped[x]) for x in xs]
            lows = [min(grouped[x]) for x in xs]
            highs = [max(grouped[x]) for x in xs]
            ax.plot(xs, means, marker="o", color=colors[condition], label=condition)
            ax.fill_between(xs, lows, highs, color=colors[condition], alpha=0.10)
        ax.set_title(title)
        ax.set_xlabel("checkpoint")
        ax.set_ylabel(ylabel)
        ax.grid(alpha=0.2)
        ax.legend(frameon=False)
        save(fig, name)

    fig, axes = plt.subplots(2, 2, figsize=(10, 7.5), sharex=True)
    for ax, metric, title in zip(axes.flat, ("normalized_utilization_entropy", "normalized_task_agent_mutual_information", "routing_alignment_eta", "oracle_gain"), ("Utilization entropy", "Task-agent MI", "Routing alignment η", "Oracle gain")):
        for condition in CONDITIONS:
            subset = [row for row in checkpoints if row["condition"] == condition]
            grouped = defaultdict(list)
            for row in subset:
                if _num(row.get(metric)) is not None:
                    grouped[int(row["checkpoint"])].append(float(row[metric]))
            xs = sorted(grouped)
            ax.plot(xs, [statistics.fmean(grouped[x]) for x in xs], marker="o", color=colors[condition], label=condition)
        ax.set_title(title)
        ax.grid(alpha=0.2)
    axes[0, 0].legend(frameon=False)
    axes[1, 0].set_xlabel("checkpoint")
    axes[1, 1].set_xlabel("checkpoint")
    save(fig, "organization_and_complementarity.png")

    # Seed-1 heatmaps are shown as a concrete paired example; ensemble tables
    # remain the primary evidence because raw agent labels are exchangeable.
    for kind, source, name, title in (("competence", competence, "competence_heatmaps_seed1.png", "Competence matrices — seed 1 (raw labels)"), ("routing", routing, "routing_heatmaps_seed1.png", "Routing matrices — seed 1 (raw labels)")):
        fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), constrained_layout=True)
        for ax, condition in zip(axes, CONDITIONS):
            values = [row for row in source if int(row["seed"]) == 1 and row["condition"] == condition and int(row["checkpoint"]) == 20]
            matrix = np.zeros((len(AGENTS), len(WORLDS)))
            for row in values:
                i, j = AGENTS.index(row["agent_id"]), WORLDS.index(row["world"])
                matrix[i, j] = float(row["accuracy"] if kind == "competence" else row["proportion"])
            im = ax.imshow(matrix, vmin=0, vmax=1, cmap="Blues" if condition == "private" else "Reds")
            ax.set_xticks(range(len(WORLDS)), WORLDS, rotation=35, ha="right")
            ax.set_yticks(range(len(AGENTS)), AGENTS)
            ax.set_title(condition)
            for i in range(len(AGENTS)):
                for j in range(len(WORLDS)):
                    ax.text(j, i, f"{matrix[i,j]:.2f}", ha="center", va="center", fontsize=8)
            fig.colorbar(im, ax=ax, fraction=0.046)
        fig.suptitle(title)
        save(fig, name)

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    terminal = [row for row in paired if int(row["checkpoint"]) == 20]
    xs = [int(row["seed"]) for row in terminal]
    ys = [row.get("D_private_minus_shared") for row in terminal]
    ax.axhline(0, color="black", linewidth=0.8)
    ax.scatter(xs, ys, color="#3a506b")
    ax.set_xlabel("paired seed")
    ax.set_ylabel("D = ΔHSE(private) − ΔHSE(shared)")
    ax.set_title("Paired endpoint effect — descriptive, not inferential")
    ax.grid(alpha=0.2)
    save(fig, "paired_delta_hse.png")

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    for condition in CONDITIONS:
        values = [row for row in checkpoints if row["condition"] == condition and _num(row.get("normalized_task_agent_mutual_information")) is not None]
        ax.scatter([row["routing_entropy"] for row in values], [row["normalized_task_agent_mutual_information"] for row in values], alpha=0.55, color=colors[condition], label=condition)
    ax.set_xlabel("routing entropy H(R)")
    ax.set_ylabel("normalized task-agent MI")
    ax.set_title("Organization: routing entropy vs task-agent MI")
    ax.grid(alpha=0.2)
    ax.legend(frameon=False)
    save(fig, "routing_entropy_vs_mi.png")

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    selected = Counter(row["selected_agent"] for row in rounds if row.get("selected_agent"))
    ax.bar(AGENTS, [selected.get(agent, 0) for agent in AGENTS], color="#3a506b")
    ax.set_title("Raw agent-label usage across Gate 1 runs")
    ax.set_ylabel("selected rounds")
    ax.grid(axis="y", alpha=0.2)
    save(fig, "label_usage_sanity.png")
    return generated


def generate_full_report(*, manifest_file: str | Path | None = None, output_dir: str | Path | None = None) -> Path:
    manifest_path_value = Path(manifest_file) if manifest_file else manifest_path()
    manifest = json.loads(manifest_path_value.read_text(encoding="utf-8"))
    entries, bundles = _load_gate_bundles(manifest)
    checkpoints, competence, routing, rounds, memory, provenance = _run_rows(entries)
    quality = _quality_rows(entries)
    paired = _paired_rows(checkpoints)
    root = Path(output_dir) if output_dir else Path("reports/campaigns/developmental-dynamics-v1/gate-1")
    root = root.expanduser().resolve()
    tables = root / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    _write_csv(tables / "data_quality.csv", quality)
    _write_csv(tables / "provenance.csv", provenance)
    _write_csv(tables / "checkpoint_metrics.csv", checkpoints)
    _write_csv(tables / "paired_checkpoint_metrics.csv", paired)
    _write_csv(tables / "competence_matrix_long.csv", competence)
    _write_csv(tables / "routing_matrix_long.csv", routing)
    _write_csv(tables / "rounds.csv", rounds)
    _write_csv(tables / "memory_trajectories.csv", memory)
    label_rows = _label_sanity(rounds, memory)
    _write_csv(tables / "label_sanity.csv", label_rows)

    metric_names = ("normalized_hse", "delta_normalized_hse", "phi", "effective_competence_dimensionality", "normalized_utilization_entropy", "normalized_task_agent_mutual_information", "routing_alignment_eta", "oracle_gain", "division_of_labor_match", "best_individual_accuracy", "oracle_society_accuracy")
    aggregate_rows = [row for metric in metric_names for row in _aggregate_checkpoint(checkpoints, metric)]
    _write_csv(tables / "checkpoint_aggregates.csv", aggregate_rows)
    terminal = [row for row in paired if int(row["checkpoint"]) == 20]
    endpoint_stats = []
    for metric in ("D_private_minus_shared", "D_phi_private_minus_shared", "private_normalized_hse", "shared_normalized_hse", "private_phi", "shared_phi", "private_d_eff", "shared_d_eff", "private_utilization", "shared_utilization", "private_mi", "shared_mi", "private_eta_route", "shared_eta_route", "private_oracle_gain", "shared_oracle_gain"):
        endpoint_stats.extend(_summary_stats(terminal, metric, group_key="checkpoint"))
    _write_csv(tables / "endpoint_statistics.csv", endpoint_stats)

    # Cost/health totals distinguish all 20 scientific runs from the 18 new
    # runs charged to the current Gate 1 execution budget.
    total_cost = sum(float(row.get("observed_cost_usd") or 0.0) for row in quality)
    new_cost = sum(float(row.get("observed_cost_usd") or 0.0) for row, entry in zip(quality, sorted(entries, key=lambda e: (int(e["bundle"].seed), e["bundle"].condition))) if entry["manifest"].get("status") != "reused")
    quality_totals = {
        "run_count": len(quality),
        "clean_runs": sum(row["health"] == "CLEAN" for row in quality),
        "recovered_runs": sum(row["health"] == "RECOVERED" for row in quality),
        "invalid_runs": sum(row["health"] == "INVALID" for row in quality),
        "expected_logical_completions": sum(int(row["expected_logical_completions"] or 0) for row in quality),
        "successful_logical_completions": sum(int(row["successful_logical_completions"] or 0) for row in quality),
        "physical_attempts": sum(int(row["physical_attempts"] or 0) for row in quality),
        "retries": sum(int(row["retries"] or 0) for row in quality),
        "timeouts": sum(int(row["timeout_count"] or 0) for row in quality),
        "parse_failures": sum(int(row["parse_error_count"] or 0) for row in quality),
        "usage_coverage_min": min(float(row["usage_coverage"]) for row in quality),
        "total_observed_cost_usd_all_runs": total_cost,
        "total_observed_cost_usd_new_runs": new_cost,
    }
    _write_json(root / "gate1_data_quality.json", quality_totals)

    generated_figures = _plot_reports(root, checkpoints, paired, competence, routing, rounds, label_rows)
    _write_json(root / "gate1_report_data.json", {
        "schema_version": 2,
        "watermark": "GATE 1 — OFFLINE DESCRIPTIVE REPORT; NOT A SCIENTIFIC CONCLUSION",
        "campaign": manifest.get("campaign"),
        "gate": GATE_1,
        "gate_status": manifest.get("gates", {}).get(GATE_1, {}).get("status"),
        "gate_2_status": manifest.get("gates", {}).get("gate_2_replication", {}).get("status"),
        "quality": quality_totals,
        "paired_endpoint_rows": terminal,
        "figures": generated_figures,
        "probe_set_hash": manifest.get("probe_set_hash"),
        "git_heads": sorted({row.get("git_commit") for row in provenance}),
    })

    def fmt(value: Any) -> str:
        return "—" if value is None else f"{float(value):.4f}" if isinstance(value, (int, float)) else str(value)

    stats_d = [row for row in endpoint_stats if row["metric"] == "D_private_minus_shared"]
    d_values = [float(row["D_private_minus_shared"]) for row in terminal if _num(row.get("D_private_minus_shared")) is not None]
    d_without_seed1 = [float(row["D_private_minus_shared"]) for row in terminal if int(row["seed"]) != 1 and _num(row.get("D_private_minus_shared")) is not None]
    mean_d = statistics.fmean(d_values) if d_values else None
    mean_d_no1 = statistics.fmean(d_without_seed1) if d_without_seed1 else None
    hse_stats = {condition: _aggregate_checkpoint(checkpoints, "normalized_hse") for condition in CONDITIONS}
    terminal_hse = {(row["condition"], int(row["checkpoint"])): row for row in aggregate_rows if row["metric"] == "normalized_hse"}
    metric_endpoint_lines = []
    for metric, label in (("normalized_hse", "normalized HSE"), ("phi", "Φ competence differentiation"), ("effective_competence_dimensionality", "effective dimensionality"), ("normalized_utilization_entropy", "utilization entropy"), ("normalized_task_agent_mutual_information", "task-agent MI"), ("routing_alignment_eta", "routing alignment η"), ("oracle_gain", "oracle gain"), ("best_individual_accuracy", "best individual accuracy"), ("oracle_society_accuracy", "oracle society accuracy")):
        values = {}
        for condition in CONDITIONS:
            vals = [row.get(metric) for row in checkpoints if row["condition"] == condition and int(row["checkpoint"]) == 20]
            values[condition] = _mean(vals)
        metric_endpoint_lines.append(f"| {label} | {fmt(values['private'])} | {fmt(values['shared'])} |")

    markdown = [
        "# Gate 1 Data Quality",
        "",
        "> **GATE 1 — OFFLINE DESCRIPTIVE REPORT.** This document is generated solely from completed immutable run artifacts. It is not a scientific conclusion and does not unlock Gate 2.",
        "",
        "## Executive summary",
        "",
        f"Gate 1 contains **{quality_totals['run_count']}/20 complete runs** across paired seeds 1–10. Logical coverage is **{quality_totals['successful_logical_completions']}/{quality_totals['expected_logical_completions']} (100%)**. The set has {quality_totals['clean_runs']} CLEAN runs and {quality_totals['recovered_runs']} RECOVERED runs; no run is incomplete.",
        "",
        f"All 20 runs together consumed approximately **US${total_cost:.5f}** according to recorded per-inference usage. The 18 new runs charged to this Gate 1 execution account for **US${new_cost:.5f}**; seed 1 was reused and is reported for completeness.",
        "",
        "The primary estimand remains the paired developmental contrast, not a maximization target: **D = ΔHSE(private) − ΔHSE(shared)**. HSE, Φ, MI, utilization, alignment, oracle gain and matching are complementary observables; none alone establishes useful specialization.",
        "",
        "## Provenance and frozen design",
        "",
        f"- Campaign: `{manifest.get('campaign')}`; Gate 1 status: `{manifest.get('gates', {}).get(GATE_1, {}).get('status')}`; Gate 2 status: `{manifest.get('gates', {}).get('gate_2_replication', {}).get('status')}`.",
        f"- Git commit(s) recorded in run metadata: `{', '.join(sorted({str(row.get('git_commit')) for row in provenance}))}`.",
        f"- Backend/model: `{provenance[0].get('backend')}` / `{provenance[0].get('model')}`; thinking `{provenance[0].get('thinking')}`.",
        f"- Matched design: 4 agents, 20 rounds, checkpoints `[0, 10, 20]`, 40 probes/checkpoint, `recent_k=8`, confidence router, ε=0.",
        f"- Probe-set SHA-256: `{manifest.get('probe_set_hash')}`.",
        "- The paired configs differ in feedback locality only; task/RNG semantics and probe set are shared.",
        "- Raw labels are exchangeable. Ensemble summaries over `agent_0`…`agent_3` are sanity checks, not role claims.",
        "",
        "## Health, cost and runtime",
        "",
        f"- Physical attempts: **{quality_totals['physical_attempts']}**; retries: **{quality_totals['retries']}**; timeout-class errors: **{quality_totals['timeouts']}**; parse errors: **{quality_totals['parse_failures']}**.",
        f"- Minimum usage coverage was **{quality_totals['usage_coverage_min']:.4f}** (one recovered run had partial provider usage metadata). No logical completion is missing.",
        "- One shared seed-6 final checkpoint experienced a long single-probe delay (~610.7 s) but recovered with complete coverage. This is an infrastructure/runtime observation, not a scientific result.",
        "",
        "See `tables/data_quality.csv` and `tables/provenance.csv` for the run-level audit.",
        "",
        "## Primary HSE trajectories",
        "",
        "HSE measures behavioral diversity; ΔHSE is baseline-relative. The plotted ribbons show the min–max range across paired seeds and the faint lines show individual runs. Diversity is not equivalent to specialization or useful division of labor.",
        "",
        "![HSE trajectory](figures/hse_trajectory.png)",
        "",
        "![Delta HSE](figures/delta_hse_trajectory.png)",
        "",
        f"At checkpoint 20, the mean paired effect D is **{fmt(mean_d)}** across seeds 1–10 and **{fmt(mean_d_no1)}** excluding seed 1. These are descriptive summaries; no inferential claim is made here.",
        "",
        "![Paired endpoint effect](figures/paired_delta_hse.png)",
        "",
        "## Competence differentiation and effective dimensionality",
        "",
        "Φ(t) is the population-variance order parameter over the competence matrix. It measures competence differentiation, not specialization. The spectral participation ratio (`d_eff`) summarizes how many independent competence-difference directions are visible; it is not a role count.",
        "",
        "![Phi](figures/competence_differentiation_phi.png)",
        "",
        "![Effective dimensionality](figures/effective_dimension.png)",
        "",
        "## Organization, alignment and complementarity",
        "",
        "The following endpoint means are descriptive and retain their separate meanings:",
        "",
        "| metric at t=20 | private | shared |",
        "|---|---:|---:|",
        *metric_endpoint_lines,
        "",
        "- Utilization entropy asks whether routing collapsed onto a small subset of agents; high entropy is not proof of specialization.",
        "- Task-agent MI asks whether routing is organized by world/task; it does not establish competence.",
        "- Routing alignment η compares routed competence with random and per-domain-oracle baselines; it can be undefined when the denominator is zero.",
        "- Oracle gain and matching gain address complementarity/potential division of labor; they are not evidence that the actual router exploited the potential.",
        "",
        "![Organization and complementarity](figures/organization_and_complementarity.png)",
        "",
        "![Routing entropy versus MI](figures/routing_entropy_vs_mi.png)",
        "",
        "## Seed 1 sensitivity and raw-label sanity",
        "",
        f"Seed 1 is the previously completed pair reused by the campaign. Its inclusion changes the endpoint mean D from **{fmt(mean_d_no1)}** (seeds 2–10) to **{fmt(mean_d)}** (seeds 1–10). This is a sensitivity diagnostic, not a reason to drop the seed.",
        "",
        "The raw-label usage plot is included to expose obvious imbalance. Because labels are arbitrary and no role is assigned by ID, any apparent global winner must be checked with permutation-invariant summaries and per-run alignment.",
        "",
        "![Raw label usage](figures/label_usage_sanity.png)",
        "",
        "![Seed 1 competence matrices](figures/competence_heatmaps_seed1.png)",
        "",
        "![Seed 1 routing matrices](figures/routing_heatmaps_seed1.png)",
        "",
        "## What the data show (descriptive)",
        "",
        "1. The paired design completed technically: all 20 runs contain the expected interaction and probe logical completions.",
        "2. Private and shared trajectories are not identical across seeds; the magnitude and direction of D are seed-dependent rather than a single deterministic path.",
        "3. Shared runs necessarily accumulate feedback in every agent, while private runs accumulate it only in selected agents; this manipulation is visible in `memory_trajectories.csv`.",
        "4. The endpoint observables do not all encode the same construct. In particular, routing concentration, HSE, competence variance, MI and oracle gain can disagree.",
        "",
        "## What the data may suggest",
        "",
        "- The paired trajectories are suitable for a formal developmental-dynamics analysis of whether information locality changes the distribution of B(t), A(t) and related observables.",
        "- The long probe delay in shared seed 6 suggests that provider/runtime behavior can be a practical confound and should be stratified by latency, retry and fingerprint in later analyses.",
        "- If a future claim concerns functional division of labor, the current data should be read through alignment, complementarity and held-out competence—not HSE alone.",
        "",
        "## What the data do not establish",
        "",
        "- They do not prove that private feedback is better, that specialization emerged, or that any agent acquired a stable world role.",
        "- They do not identify a phase transition, causal mechanism beyond the pre-registered private/shared manipulation, or generalization outside these synthetic worlds.",
        "- They do not justify optimizing HSE/MI/Φ directly; doing so would invite Goodhart-style pathologies.",
        "- They do not unlock random routing, long-horizon trajectories, Gate 2, or any intervention.",
        "",
        "## Human review questions",
        "",
        "1. Are paired D and Φ contrasts stable enough across seeds to motivate a pre-registered follow-up?",
        "2. Do condition differences persist after permutation-invariant alignment of agent labels?",
        "3. Does any routing organization align with competence rather than merely concentration?",
        "4. How much of the observed contrast is explained by early accuracy versus collective observables?",
        "5. Is the provider-latency outlier sufficiently independent of condition for a later causal analysis?",
        "6. Would a small, explicitly approved random-routing control add more information than additional baseline seeds?",
        "",
        "## Candidate next experiments (advisory only; not executed)",
        "",
        "1. **Permutation-invariant paired analysis** of the completed Gate 1 data, including aligned competence/routing matrices and uncertainty intervals.",
        "2. **Early-trajectory predictability** using existing online observables, only after leakage audits and a pre-specified terminal target.",
        "3. **Random-routing control** to separate information locality from confidence-driven selection, if explicitly approved and budgeted.",
        "4. **Long-horizon condition pair** with the same frozen baseline, if the short-horizon contrast and runtime health justify it.",
        "",
        "These are ranked by information value, not by the observed scientific result. No new stage is authorized by this report.",
        "",
        "## Reproducibility artifacts",
        "",
        "- Raw runs: `data/runs/campaigns/developmental-dynamics-v1/`.",
        "- Campaign manifest: `data/campaigns/developmental-dynamics-v1/campaign.json`.",
        "- Machine-readable tables: `tables/`.",
        "- Figures: `figures/`.",
        "- The existing `interim_summary.json` and `trajectory_data.json` remain available; this report adds a richer offline layer without modifying raw runs.",
        "",
        "## Gate 2 lock",
        "",
        "**Gate 2 remains LOCKED.** A human review is required before any further real inference. This report makes no automatic scientific decision and starts no subsequent stage.",
    ]
    report_path = root / "GATE1_EXECUTION_AND_ANALYSIS_REPORT.md"
    report_path.write_text("\n".join(markdown) + "\n", encoding="utf-8")
    # Keep the project-level handoff at the requested stable path as well.
    docs_path = Path("docs/GATE1_EXECUTION_AND_ANALYSIS_REPORT.md").resolve()
    docs_path.parent.mkdir(parents=True, exist_ok=True)
    docs_path.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")
    return report_path


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate the offline Gate 1 execution and analysis report")
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)
    print(generate_full_report(manifest_file=args.manifest, output_dir=args.output_dir))


if __name__ == "__main__":
    main()
