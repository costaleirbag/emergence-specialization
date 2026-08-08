"""Offline report for the partial random-routing mechanism control.

The module reads immutable artifacts only.  It never constructs a provider or
performs an inference call.  Incomplete runs are retained in the health table
but are never silently included in endpoint aggregates.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from .analysis import checkpoint_rows, competence_rows, load_run, round_rows, routing_rows
from .campaign import _health_for
from .gate1_report import _analysis_seed, _num, _write_csv, _write_json
from .metrics.information import mi_null_diagnostic
from .metrics.online import online_team_accuracy

WORLDS = ("ALPHA", "BETA", "GAMMA", "DELTA")
AGENTS = ("agent_0", "agent_1", "agent_2", "agent_3")
CONDITIONS = ("private", "shared")
RANDOM_ROOT = Path("data/runs/campaigns/developmental-dynamics-v1")
MANIFEST = Path("data/campaigns/developmental-dynamics-v1/campaign.json")


def _health_name(health: dict[str, Any]) -> str:
    return {"healthy": "CLEAN", "healthy_recovered": "RECOVERED", "invalid": "INVALID"}.get(
        str(health.get("health_flag")), "UNKNOWN"
    )


def _entry(path: Path, require_completed: bool = False) -> dict[str, Any]:
    metadata = json.loads((path / "metadata.json").read_text(encoding="utf-8"))
    cfg = metadata["config"]
    health = _health_for(path)
    bundle = load_run(path, require_completed=True, require_checkpoints=True) if require_completed else None
    return {
        "path": path,
        "metadata": metadata,
        "config": cfg,
        "health": health,
        "bundle": bundle,
        "seed": int(cfg["experiment"]["seed"]),
        "condition": str(cfg["condition"]["memory_mode"]),
        "router": str(cfg["router"]["strategy"]),
    }


def _random_entries() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    all_entries: list[dict[str, Any]] = []
    complete: list[dict[str, Any]] = []
    for metadata_path in sorted(RANDOM_ROOT.glob("*/metadata.json")):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            cfg = metadata.get("config", {})
            if cfg.get("router", {}).get("strategy") != "random":
                continue
            seed = int(cfg.get("experiment", {}).get("seed"))
            condition = cfg.get("condition", {}).get("memory_mode")
            if seed not in range(1, 11) or condition not in CONDITIONS:
                continue
            path = metadata_path.parent
            all_entry = _entry(path)
            all_entries.append(all_entry)
            if all_entry["health"].get("health_flag") in {"healthy", "healthy_recovered"}:
                complete.append(_entry(path, require_completed=True))
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            continue
    return all_entries, complete


def _confidence_entries() -> list[dict[str, Any]]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries: list[dict[str, Any]] = []
    for row in manifest.get("runs", []):
        if row.get("gate") != "gate_1_replication" or not row.get("run_dir"):
            continue
        try:
            entry = _entry(Path(row["run_dir"]), require_completed=True)
            if entry["router"] == "confidence":
                entries.append(entry)
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            continue
    return sorted(entries, key=lambda e: (e["seed"], e["condition"]))


def _trajectory(entry: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [dict(row) for row in checkpoint_rows(entry["bundle"])]
    baseline_hse = next((row.get("normalized_hse") for row in rows if int(row["checkpoint"]) == 0), None)
    baseline_phi = next((row.get("phi") for row in rows if int(row["checkpoint"]) == 0), None)
    for row in rows:
        row["delta_hse"] = row.get("normalized_hse") - baseline_hse if _num(row.get("normalized_hse")) is not None and _num(baseline_hse) is not None else None
        row["delta_phi"] = row.get("phi") - baseline_phi if _num(row.get("phi")) is not None and _num(baseline_phi) is not None else None
        row["router"] = entry["router"]
        row["health"] = _health_name(entry["health"])
    return sorted(rows, key=lambda row: int(row["checkpoint"]))


def _pair_audit(entries: list[dict[str, Any]], router: str) -> list[dict[str, Any]]:
    by_seed: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    for entry in entries:
        by_seed[entry["seed"]][entry["condition"]] = entry
    rows: list[dict[str, Any]] = []
    for seed, conditions in sorted(by_seed.items()):
        if not all(condition in conditions for condition in CONDITIONS):
            continue
        private, shared = conditions["private"], conditions["shared"]
        p_rounds, s_rounds = round_rows(private["bundle"]), round_rows(shared["bundle"])
        task_equal = len(p_rounds) == len(s_rounds) and all(
            (a.get("world"), a.get("x"), a.get("y"), a.get("correct_answer"))
            == (b.get("world"), b.get("x"), b.get("y"), b.get("correct_answer"))
            for a, b in zip(p_rounds, s_rounds)
        )
        route_equal = len(p_rounds) == len(s_rounds) and all(a.get("selected_agent") == b.get("selected_agent") for a, b in zip(p_rounds, s_rounds))
        rows.append({
            "router": router,
            "seed": seed,
            "task_sequence_equal": task_equal,
            "selected_sequence_equal": route_equal,
            "private_feedback_recipient_counts": sorted({int(row.get("feedback_recipient_count", -1)) for row in p_rounds}),
            "shared_feedback_recipient_counts": sorted({int(row.get("feedback_recipient_count", -1)) for row in s_rounds}),
            "private_rounds": len(p_rounds),
            "shared_rounds": len(s_rounds),
        })
    return rows


def _quality(entries: list[dict[str, Any]], gate: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in entries:
        health = entry["health"]
        summary = json.loads((entry["path"] / "summary.json").read_text(encoding="utf-8"))
        rows.append({
            "gate": gate,
            "seed": entry["seed"],
            "condition": entry["condition"],
            "router": entry["router"],
            "run_id": summary.get("run_id"),
            "run_dir": str(entry["path"]),
            "status": health.get("status"),
            "health": _health_name(health),
            "expected_logical_completions": health.get("expected_logical_completions"),
            "successful_logical_completions": health.get("successful_logical_completions"),
            "missing_logical_completions": health.get("missing_logical_completions"),
            "completion_coverage": health.get("completion_coverage"),
            "physical_attempts": health.get("physical_attempts"),
            "retries": health.get("retries"),
            "parse_error_count": health.get("parse_error_count"),
            "empty_content_count": health.get("empty_content_count"),
            "timeout_count": health.get("timeout_count"),
            "rate_limit_count": health.get("rate_limit_count"),
            "usage_coverage": health.get("usage_coverage"),
            "observed_cost_usd": health.get("observed_cost_usd"),
            "latency_mean_s": (health.get("latency_s") or {}).get("mean"),
            "latency_median_s": (health.get("latency_s") or {}).get("median"),
            "latency_max_s": (health.get("latency_s") or {}).get("max"),
        })
    return sorted(rows, key=lambda row: (row["gate"], int(row["seed"]), row["condition"]))


def _contrast(rows: list[dict[str, Any]], metric: str) -> list[dict[str, Any]]:
    by_seed: dict[int, dict[str, float]] = defaultdict(dict)
    for row in rows:
        if int(row["checkpoint"]) != 20 or _num(row.get(metric)) is None:
            continue
        by_seed[int(row["seed"])][str(row["condition"])] = float(row[metric])
    return [{"seed": seed, "private_minus_shared": values["private"] - values["shared"]} for seed, values in sorted(by_seed.items()) if all(c in values for c in CONDITIONS)]


def _null_rows(entries: list[dict[str, Any]], permutations: int = 2000) -> list[dict[str, Any]]:
    out = []
    for entry in entries:
        rows = round_rows(entry["bundle"])
        diagnostic = mi_null_diagnostic(
            [str(row["world"]) for row in rows],
            [str(row["selected_agent"]) for row in rows],
            permutations=permutations,
            seed=_analysis_seed(entry["bundle"].run_id, "random10-mi-null-v1"),
        )
        counts: dict[str, int] = defaultdict(int)
        for row in rows:
            counts[str(row["selected_agent"])] += 1
        total = sum(counts.values())
        entropy = -sum((value / total) * math.log2(value / total) for value in counts.values() if value) if total else 0.0
        normalized_entropy = entropy / math.log2(len(AGENTS)) if len(AGENTS) > 1 else 0.0
        out.append({"seed": entry["seed"], "condition": entry["condition"], "router": entry["router"], "normalized_routing_entropy": normalized_entropy, **diagnostic})
    return sorted(out, key=lambda row: (int(row["seed"]), row["condition"]))


def _online_rows(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"seed": entry["seed"], "condition": entry["condition"], "router": entry["router"], **online_team_accuracy(entry["bundle"].events)} for entry in entries]


def _summary(values: list[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "mean": statistics.fmean(values) if values else None,
        "median": statistics.median(values) if values else None,
        "std_population": statistics.pstdev(values) if len(values) > 1 else (0.0 if values else None),
        "fraction_positive": sum(value > 0 for value in values) / len(values) if values else None,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
    }


def _plots(root: Path, confidence_rows: list[dict[str, Any]], random_rows: list[dict[str, Any]], contrasts: dict[str, list[dict[str, Any]]], random_entries: list[dict[str, Any]]) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    directory = root / "figures"
    directory.mkdir(parents=True, exist_ok=True)
    generated: list[str] = []

    def save(fig: Any, name: str) -> None:
        try:
            fig.tight_layout()
        except RuntimeError:
            pass
        fig.savefig(directory / name, dpi=180, bbox_inches="tight")
        plt.close(fig)
        generated.append(f"figures/{name}")

    colors = {"private": "#276fbf", "shared": "#b23a48"}
    for metric, filename, title, ylabel in (
        ("delta_hse", "delta_hse_all_cells.png", "Developmental HSE contrast", "Δ normalized HSE"),
        ("delta_phi", "delta_phi_all_cells.png", "Competence differentiation contrast", "ΔΦ"),
    ):
        fig, ax = plt.subplots(figsize=(8.5, 4.8))
        for router, rows in (("confidence", confidence_rows), ("random", random_rows)):
            for condition in CONDITIONS:
                subset = [row for row in rows if row["router"] == router and row["condition"] == condition]
                grouped: dict[int, list[float]] = defaultdict(list)
                for row in subset:
                    if _num(row.get(metric)) is not None:
                        grouped[int(row["checkpoint"])].append(float(row[metric]))
                xs = sorted(grouped)
                if xs:
                    linestyle = "-" if router == "confidence" else "--"
                    ax.plot(xs, [statistics.fmean(grouped[x]) for x in xs], marker="o", linestyle=linestyle, color=colors[condition], label=f"{router} / {condition}")
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_xlabel("checkpoint")
        ax.set_ylabel(ylabel)
        ax.set_title(title + " — descriptive; random gate partial")
        ax.grid(alpha=0.2)
        ax.legend(frameon=False, ncol=2)
        save(fig, filename)

    for name, key, label, color in (("g_hse_by_seed.png", "G_HSE", "G_HSE", "#3a506b"), ("g_phi_by_seed.png", "G_Phi", "G_Φ", "#6a4c93")):
        fig, ax = plt.subplots(figsize=(8.5, 4.8))
        rows = contrasts.get(key, [])
        ax.axhline(0, color="black", linewidth=0.8)
        if rows:
            ax.bar([str(row["seed"]) for row in rows], [row["private_minus_shared"] for row in rows], color=color)
        ax.set_xlabel("paired seed")
        ax.set_ylabel(label)
        ax.set_title(label + " — confidence minus random")
        ax.grid(axis="y", alpha=0.2)
        save(fig, name)

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    for router, rows in (("confidence", confidence_rows), ("random", random_rows)):
        for condition in CONDITIONS:
            subset = [row for row in rows if row["router"] == router and row["condition"] == condition and int(row["checkpoint"]) == 20]
            if subset:
                ax.scatter([row["normalized_utilization_entropy"] for row in subset], [row["oracle_gain"] for row in subset], label=f"{router} / {condition}", alpha=0.75)
    ax.set_xlabel("normalized utilization entropy")
    ax.set_ylabel("oracle gain")
    ax.set_title("Utilization vs complementarity potential")
    ax.grid(alpha=0.2)
    ax.legend(frameon=False, ncol=2)
    save(fig, "utilization_vs_oracle_gain.png")

    null_rows = _null_rows(random_entries)
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    for condition in CONDITIONS:
        subset = [row for row in null_rows if row["condition"] == condition]
        if subset:
            ax.scatter([row["normalized_routing_entropy"] for row in subset], [row["normalized_excess_mi"] for row in subset], label=f"random / {condition}")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("normalized routing entropy")
    ax.set_ylabel("normalized MI excess over permutation null")
    ax.set_title("Random-routing MI null diagnostic")
    ax.grid(alpha=0.2)
    ax.legend(frameon=False)
    save(fig, "random_mi_null.png")

    # A readable representative heatmap; all matrices remain in CSV tables.
    if random_entries:
        fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.0), constrained_layout=True)
        seed = min(entry["seed"] for entry in random_entries)
        for ax, condition in zip(axes, CONDITIONS):
            entry = next((item for item in random_entries if item["seed"] == seed and item["condition"] == condition), None)
            matrix = np.zeros((len(AGENTS), len(WORLDS)))
            if entry is not None:
                for row in competence_rows(entry["bundle"]):
                    if int(row["checkpoint"]) == 20:
                        matrix[AGENTS.index(row["agent_id"]), WORLDS.index(row["world"])] = float(row["accuracy"])
            im = ax.imshow(matrix, vmin=0, vmax=1, cmap="Blues" if condition == "private" else "Reds")
            ax.set_title(f"random / {condition} / seed {seed}")
            ax.set_xticks(range(4), WORLDS, rotation=30, ha="right")
            ax.set_yticks(range(4), AGENTS)
            for i in range(4):
                for j in range(4):
                    ax.text(j, i, f"{matrix[i, j]:.2f}", ha="center", va="center", fontsize=8)
            fig.colorbar(im, ax=ax, fraction=0.046)
        save(fig, "random_seed1_competence_heatmaps.png")
    return generated


def generate_report(*, output_dir: str | Path = "reports/campaigns/developmental-dynamics-v1/random-routing-10") -> Path:
    root = Path(output_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    tables = root / "tables"
    tables.mkdir(parents=True, exist_ok=True)

    random_all, random_complete = _random_entries()
    confidence = _confidence_entries()
    random_cp = [row for entry in random_complete for row in _trajectory(entry)]
    confidence_cp = [row for entry in confidence for row in _trajectory(entry)]
    for row in random_cp + confidence_cp:
        row["run_id"] = next(entry["bundle"].run_id for entry in random_complete + confidence if entry["bundle"].run_id == row["run_id"]) if row.get("run_id") else row.get("run_id")
    # The helper above already includes router/health; retain a compact machine
    # readable table with both cells and both routing mechanisms.
    _write_csv(tables / "checkpoint_metrics.csv", random_cp + confidence_cp)
    _write_csv(tables / "health_inventory.csv", _quality(random_all, "gate_random_routing_10") + _quality(confidence, "gate_1_replication"))
    random_audit = _pair_audit(random_complete, "random")
    confidence_audit = _pair_audit(confidence, "confidence")
    _write_csv(tables / "paired_sequence_audit.csv", random_audit + confidence_audit)
    _write_csv(tables / "competence_matrix_long.csv", [row for entry in random_complete + confidence for row in competence_rows(entry["bundle"])])
    _write_csv(tables / "routing_matrix_long.csv", [row for entry in random_complete + confidence for row in routing_rows(entry["bundle"])])
    online = _online_rows(random_complete + confidence)
    _write_csv(tables / "online_accuracy.csv", online)
    nulls = _null_rows(random_complete)
    _write_csv(tables / "random_mi_null.csv", nulls)

    contrasts: dict[str, list[dict[str, Any]]] = {}
    for name, metric in (("D_conf_HSE", "delta_hse"), ("D_conf_Phi", "delta_phi")):
        contrasts[name] = _contrast(confidence_cp, metric)
    for name, metric in (("D_rand_HSE", "delta_hse"), ("D_rand_Phi", "delta_phi")):
        contrasts[name] = _contrast(random_cp, metric)
    conf_hse = {int(row["seed"]): float(row["private_minus_shared"]) for row in contrasts["D_conf_HSE"]}
    rand_hse = {int(row["seed"]): float(row["private_minus_shared"]) for row in contrasts["D_rand_HSE"]}
    contrasts["G_HSE"] = [{"seed": seed, "private_minus_shared": conf_hse[seed] - rand_hse[seed]} for seed in sorted(set(conf_hse) & set(rand_hse))]
    conf_phi = {int(row["seed"]): float(row["private_minus_shared"]) for row in contrasts["D_conf_Phi"]}
    rand_phi = {int(row["seed"]): float(row["private_minus_shared"]) for row in contrasts["D_rand_Phi"]}
    contrasts["G_Phi"] = [{"seed": seed, "private_minus_shared": conf_phi[seed] - rand_phi[seed]} for seed in sorted(set(conf_phi) & set(rand_phi))]
    contrast_table = []
    for seed in sorted({int(row["seed"]) for rows in contrasts.values() for row in rows}):
        contrast_table.append({"seed": seed, **{name: next((row["private_minus_shared"] for row in rows if int(row["seed"]) == seed), None) for name, rows in contrasts.items()}})
    _write_csv(tables / "mechanism_contrasts.csv", contrast_table)

    random_quality = _quality(random_all, "gate_random_routing_10")
    random_cost = sum(float(row.get("observed_cost_usd") or 0.0) for row in random_quality)
    summary = {
        "status": "PARTIAL_BLOCKED",
        "gate": "gate_random_routing_10",
        "planned_pairs": list(range(1, 11)),
        "complete_pairs": sorted({int(row["seed"]) for row in random_audit if row["task_sequence_equal"] and row["selected_sequence_equal"]}),
        "complete_runs": len(random_complete),
        "health_counts": {label: sum(row["health"] == label for row in random_quality) for label in ("CLEAN", "RECOVERED", "INVALID")},
        "logical_expected": sum(int(row.get("expected_logical_completions") or 0) for row in random_quality),
        "logical_successful": sum(int(row.get("successful_logical_completions") or 0) for row in random_quality),
        "physical_attempts": sum(int(row.get("physical_attempts") or 0) for row in random_quality),
        "retries": sum(int(row.get("retries") or 0) for row in random_quality),
        "parse_errors": sum(int(row.get("parse_error_count") or 0) for row in random_quality),
        "empty_content": sum(int(row.get("empty_content_count") or 0) for row in random_quality),
        "timeouts": sum(int(row.get("timeout_count") or 0) for row in random_quality),
        "rate_limits": sum(int(row.get("rate_limit_count") or 0) for row in random_quality),
        "observed_cost_usd": random_cost,
        "hard_budget_usd": 1.0,
        "physical_ceiling": 14000,
        "probe_set_hash": "cb234422389ff7d5a04566112a483f147e4a3d1212b1c69fbb0396ec9ca4c55e",
        "contrasts": {name: _summary([float(row["private_minus_shared"]) for row in rows]) for name, rows in contrasts.items()},
        "sequence_audit": random_audit,
        "mi_null": nulls,
    }
    summary["figures"] = _plots(root, confidence_cp, random_cp, contrasts, random_complete)
    _write_json(root / "mechanism_summary.json", summary)
    return _write_markdown(root, summary, random_quality, random_audit, contrasts)


def _write_markdown(root: Path, summary: dict[str, Any], quality: list[dict[str, Any]], audit: list[dict[str, Any]], contrasts: dict[str, list[dict[str, Any]]]) -> Path:
    def fmt(value: Any) -> str:
        return "—" if value is None else f"{float(value):+.4f}" if isinstance(value, (int, float)) else str(value)

    lines = [
        "# Random-routing mechanism control",
        "",
        "> **STATUS: PARTIAL / BLOCKED.** Offline descriptive report only. The pre-specified ten-pair control stopped after an incomplete private seed-3 run; no later seeds were started.",
        "",
        "## Scope and health gate",
        "",
        "This control was designed to separate information locality from confidence-driven selection: the random router is paired across private and shared feedback, with the Gate 1 confidence baseline retained as a separate reference. The official runner completed random seeds 1–2 and stopped at private seed 3 after both attempts for one probe returned `answer: 7`, outside the allowed answer domain `[0, 6]`. The resulting run has 201 missing logical probe completions and is invalid/incomplete; it is not included in endpoint aggregates.",
        "",
        f"Random control: **{len(summary['complete_runs']) if isinstance(summary['complete_runs'], list) else summary['complete_runs']}/20 runs complete**, **{len(summary['complete_pairs']) if isinstance(summary['complete_pairs'], list) else 0}/10 pairs complete**, observed cost **US${summary['observed_cost_usd']:.6f}**, physical attempts **{summary['physical_attempts']}**, retries **{summary['retries']}**, parse errors **{summary['parse_errors']}**, empty-content errors **{summary['empty_content']}**, timeouts **{summary['timeouts']}**, rate limits **{summary['rate_limits']}**. The hard cap was US$1.00 and the physical ceiling was 14,000.",
        "",
        "The failed artifact remains in `health_inventory.csv`; it is not silently discarded.",
        "",
        "## Pre-specified contrasts",
        "",
        "At checkpoint 20: `D_conf_HSE = ΔHSE(confidence/private) − ΔHSE(confidence/shared)`, `D_rand_HSE = ΔHSE(random/private) − ΔHSE(random/shared)`, and `G_HSE = D_conf_HSE − D_rand_HSE`. The Φ contrasts are defined analogously. These are descriptive paired quantities, not inferential estimates.",
        "",
        "| contrast | n | mean | median | fraction positive |",
        "|---|---:|---:|---:|---:|",
    ]
    for name in ("D_conf_HSE", "D_rand_HSE", "G_HSE", "D_conf_Phi", "D_rand_Phi", "G_Phi"):
        values = [float(row["private_minus_shared"]) for row in contrasts.get(name, [])]
        stats = summary["contrasts"].get(name, {})
        lines.append(f"| {name} | {stats.get('n', 0)} | {fmt(stats.get('mean'))} | {fmt(stats.get('median'))} | {fmt(stats.get('fraction_positive'))} |")
    lines += [
        "",
        "The random contrast has n=2 pairs. It is therefore a plumbing/measurement result, not evidence for a mechanism or effect size. Confidence and random controls also differ in sample size and health history here.",
        "",
        "## Pairing and semantics",
        "",
        "For random seeds 1–2, private/shared task tuples and selected-agent sequences match exactly. Every private round has one recipient; every shared round has four. Random routing does not consult confidence. Probe evaluation uses a state snapshot and does not update controlled memory.",
        "",
        "| seed | task sequence equal | selected sequence equal | private recipient counts | shared recipient counts |",
        "|---:|:---:|:---:|---|---|",
    ]
    for row in audit:
        if row["router"] == "random":
            lines.append(f"| {row['seed']} | {row['task_sequence_equal']} | {row['selected_sequence_equal']} | {row['private_feedback_recipient_counts']} | {row['shared_feedback_recipient_counts']} |")
    lines += [
        "",
        "## Random-routing MI null",
        "",
        "The permutation diagnostic fixes the observed world sequence and shuffles selected-agent labels. It is a finite-sample sanity check, not a p-value.",
        "",
        "![Random MI null](figures/random_mi_null.png)",
        "",
        "## Figures and tables",
        "",
        "- `tables/health_inventory.csv` — all random and Gate 1 health/provenance rows.",
        "- `tables/paired_sequence_audit.csv` — exact task/route and recipient checks.",
        "- `tables/mechanism_contrasts.csv` — per-seed D/G values.",
        "- `tables/checkpoint_metrics.csv` — B(t), Φ(t), utilization, MI, alignment, oracle and matching diagnostics.",
        "- `tables/competence_matrix_long.csv`, `tables/routing_matrix_long.csv`, `tables/online_accuracy.csv`.",
        "",
        "![Developmental HSE](figures/delta_hse_all_cells.png)",
        "",
        "![Developmental Phi](figures/delta_phi_all_cells.png)",
        "",
        "![Mechanism HSE](figures/g_hse_by_seed.png)",
        "",
        "![Mechanism Phi](figures/g_phi_by_seed.png)",
        "",
        "## Interpretation boundary",
        "",
        "The completed random pairs validate the plumbing of a paired random-routing control, but not the ten-pair experiment. A difference between random/private and random/shared cannot be separated from seed variation with two pairs. The invalid seed-3 response is a runtime/model-output validity issue, not a scientific result. No claim of specialization, useful division of labor, or causal mechanism is warranted.",
        "",
        "**Gate 2 remains LOCKED.** No long-horizon, softmax, locality sweep, intervention, or other model experiment was started.",
        "",
        "## Provenance",
        "",
        "- Raw artifacts: `data/runs/campaigns/developmental-dynamics-v1/`.",
        "- Campaign manifest: `data/campaigns/developmental-dynamics-v1/campaign.json`.",
        "- Pre-run tooling HEAD: `c2a7e3e`.",
        "- Probe-set hash: `cb234422389ff7d5a04566112a483f147e4a3d1212b1c69fbb0396ec9ca4c55e`.",
        "",
        "Do not launch further inference from this report without human review of the invalid seed-3 run and an explicit decision about whether to resume the pre-specified gate.",
    ]
    report_path = root / "MECHANISM_REPORT.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    docs_path = Path("docs/RANDOM_ROUTING_MECHANISM_REPORT.md")
    docs_path.parent.mkdir(parents=True, exist_ok=True)
    docs_path.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")
    return report_path


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate the offline random-routing mechanism report")
    parser.add_argument("--output-dir", default="reports/campaigns/developmental-dynamics-v1/random-routing-10")
    args = parser.parse_args(list(argv) if argv is not None else None)
    print(generate_report(output_dir=args.output_dir))


if __name__ == "__main__":
    main()
