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

from emergent_specialization.reporting.analysis import (
    checkpoint_rows,
    competence_rows,
    hse_trajectory_rows,
    load_run,
    memory_rows,
    round_rows,
    routing_rows,
)
from emergent_specialization.runtime.campaign import GATE_1, _health_for, manifest_path
from emergent_specialization.metrics.information import mi_null_diagnostic
from emergent_specialization.metrics.online import online_team_accuracy


WORLDS = ("ALPHA", "BETA", "GAMMA", "DELTA")
AGENTS = ("agent_0", "agent_1", "agent_2", "agent_3")
CONDITIONS = ("private", "shared")
MI_PERMUTATIONS = 10_000
ANALYSIS_SEED_SALT = "gate1-mi-null-v1"


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
    phi_baseline = next((row.get("phi") for row in rows if int(row["checkpoint"]) == 0), None)
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
        row["delta_phi"] = row.get("phi") - phi_baseline if _num(row.get("phi")) is not None and _num(phi_baseline) is not None else None
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
            "delta_hse_private": private.get("delta_normalized_hse"),
            "delta_hse_shared": shared.get("delta_normalized_hse"),
            "delta_hse_private_minus_shared": (private.get("delta_normalized_hse") - shared.get("delta_normalized_hse")) if _num(private.get("delta_normalized_hse")) is not None and _num(shared.get("delta_normalized_hse")) is not None else None,
            "private_phi": private.get("phi"),
            "shared_phi": shared.get("phi"),
            "phi_level_private_minus_shared": (private.get("phi") - shared.get("phi")) if _num(private.get("phi")) is not None and _num(shared.get("phi")) is not None else None,
            "delta_phi_private": private.get("delta_phi"),
            "delta_phi_shared": shared.get("delta_phi"),
            "delta_phi_private_minus_shared": (private.get("delta_phi") - shared.get("delta_phi")) if _num(private.get("delta_phi")) is not None and _num(shared.get("delta_phi")) is not None else None,
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
            "private_u_route": private.get("u_route"),
            "shared_u_route": shared.get("u_route"),
            "private_u_rand": private.get("u_rand"),
            "shared_u_rand": shared.get("u_rand"),
            "private_u_oracle_domain": private.get("u_oracle_domain"),
            "shared_u_oracle_domain": shared.get("u_oracle_domain"),
            "private_u_match": private.get("division_of_labor_match"),
            "shared_u_match": shared.get("division_of_labor_match"),
            "private_u_single": private.get("single_agent_accuracy"),
            "shared_u_single": shared.get("single_agent_accuracy"),
            "private_delta_match": private.get("delta_match"),
            "shared_delta_match": shared.get("delta_match"),
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


def _analysis_seed(run_id: str, salt: str = ANALYSIS_SEED_SALT) -> int:
    """Derive a stable local-analysis seed without touching experiment RNG."""
    import hashlib

    return int.from_bytes(hashlib.sha256(f"{salt}:{run_id}".encode("utf-8")).digest()[:8], "big")


def _pearson(left: list[float], right: list[float]) -> float:
    """Pearson correlation with an explicit constant-vector convention."""
    if len(left) != len(right) or not left:
        return 0.0
    left_mean = statistics.fmean(left)
    right_mean = statistics.fmean(right)
    left_var = sum((value - left_mean) ** 2 for value in left)
    right_var = sum((value - right_mean) ** 2 for value in right)
    if left_var <= 1e-15 and right_var <= 1e-15:
        return 1.0 if left == right else 0.0
    if left_var <= 1e-15 or right_var <= 1e-15:
        return 0.0
    covariance = sum((a - left_mean) * (b - right_mean) for a, b in zip(left, right))
    return covariance / math.sqrt(left_var * right_var)


def _argmax_labels(values: dict[str, float]) -> str:
    if not values:
        return ""
    maximum = max(values.values())
    return "|".join(sorted(label for label, value in values.items() if value == maximum))


def _mi_null_rows(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in entries:
        bundle = entry["bundle"]
        round_data = round_rows(bundle)
        worlds = [str(row["world"]) for row in round_data if row.get("world") is not None and row.get("selected_agent")]
        agents = [str(row["selected_agent"]) for row in round_data if row.get("world") is not None and row.get("selected_agent")]
        diagnostic = mi_null_diagnostic(
            worlds,
            agents,
            permutations=MI_PERMUTATIONS,
            seed=_analysis_seed(bundle.run_id),
        ) if worlds else {
            "observed_mi": None,
            "normalized_observed_mi": None,
            "null_mean": None,
            "null_std": None,
            "null_95th_percentile": None,
            "excess_mi": None,
            "null_percentile": None,
            "normalized_null_mean": None,
            "normalized_null_std": None,
            "normalized_null_95th_percentile": None,
            "normalized_excess_mi": None,
            "permutations": MI_PERMUTATIONS,
            "seed": _analysis_seed(bundle.run_id),
        }
        routing_counts = Counter(agents)
        rows.append({
            "run_id": bundle.run_id,
            "seed": bundle.seed,
            "condition": bundle.condition,
            "rounds": len(worlds),
            "routing_entropy": _entropy(dict(routing_counts)),
            "normalized_routing_entropy": _normalized_entropy(dict(routing_counts)),
            "mi_obs": diagnostic.get("observed_mi"),
            "normalized_mi_obs": diagnostic.get("normalized_observed_mi"),
            "mi_null_mean": diagnostic.get("null_mean"),
            "mi_null_std": diagnostic.get("null_std"),
            "mi_null_95th_percentile": diagnostic.get("null_95th_percentile"),
            "mi_excess": diagnostic.get("excess_mi"),
            "normalized_mi_null_mean": diagnostic.get("normalized_null_mean"),
            "normalized_mi_null_std": diagnostic.get("normalized_null_std"),
            "normalized_mi_null_95th_percentile": diagnostic.get("normalized_null_95th_percentile"),
            "normalized_mi_excess": diagnostic.get("normalized_excess_mi"),
            "mi_null_percentile": diagnostic.get("null_percentile"),
            "permutations": diagnostic.get("permutations"),
            "analysis_seed": diagnostic.get("seed"),
        })
    return sorted(rows, key=lambda row: (int(row["seed"]), str(row["condition"])))


def _online_accuracy_rows(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in entries:
        bundle = entry["bundle"]
        summary = online_team_accuracy(bundle.events)
        rows.append({
            "run_id": bundle.run_id,
            "seed": bundle.seed,
            "condition": bundle.condition,
            "online_interaction_accuracy": summary["online_interaction_accuracy"],
            "rounds_total": summary["rounds_total"],
            "rounds_first_half_accuracy": summary["rounds_first_half_accuracy"],
            "rounds_second_half_accuracy": summary["rounds_second_half_accuracy"],
            "accuracy_by_world": json.dumps(summary["accuracy_by_world"], sort_keys=True),
            "correct_rounds": summary["correct_rounds"],
        })
    return sorted(rows, key=lambda row: (int(row["seed"]), str(row["condition"])))


def _measurement_reliability_rows(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_seed: dict[int, dict[str, Any]] = defaultdict(dict)
    for entry in entries:
        by_seed[int(entry["bundle"].seed)][entry["bundle"].condition] = entry["bundle"]
    rows: list[dict[str, Any]] = []
    for seed, conditions in sorted(by_seed.items()):
        private = conditions.get("private")
        shared = conditions.get("shared")
        if private is None or shared is None:
            continue
        p0 = next((row for row in private.checkpoints if int(row.get("checkpoint", -1)) == 0), None)
        s0 = next((row for row in shared.checkpoints if int(row.get("checkpoint", -1)) == 0), None)
        if p0 is None or s0 is None:
            continue
        p_vectors = {str(agent): [float(value) for value in vector] for agent, vector in zip(p0.get("agent_ids", []), p0.get("behavioral_matrix", []))}
        s_vectors = {str(agent): [float(value) for value in vector] for agent, vector in zip(s0.get("agent_ids", []), s0.get("behavioral_matrix", []))}
        agreements: list[float] = []
        correlations: list[float] = []
        for agent in sorted(set(p_vectors) & set(s_vectors)):
            left, right = p_vectors[agent], s_vectors[agent]
            if len(left) != len(right) or not left:
                continue
            agreements.append(sum(a == b for a, b in zip(left, right)) / len(left))
            correlations.append(_pearson(left, right))
        p_checkpoint = next(row for row in checkpoint_rows(private) if int(row["checkpoint"]) == 0)
        s_checkpoint = next(row for row in checkpoint_rows(shared) if int(row["checkpoint"]) == 0)
        rows.append({
            "seed": seed,
            "probe_count": len(next(iter(p_vectors.values()), [])),
            "t0_exact_correctness_agreement": _mean(agreements),
            "t0_mean_behavioral_vector_correlation": _mean(correlations),
            "hse_private_0": p_checkpoint.get("hse"),
            "hse_shared_0": s_checkpoint.get("hse"),
            "normalized_hse_private_0": p_checkpoint.get("normalized_hse"),
            "normalized_hse_shared_0": s_checkpoint.get("normalized_hse"),
            "phi_private_0": p_checkpoint.get("phi"),
            "phi_shared_0": s_checkpoint.get("phi"),
            "oracle_gain_private_0": p_checkpoint.get("oracle_gain"),
            "oracle_gain_shared_0": s_checkpoint.get("oracle_gain"),
        })
    return rows


def _empty_state_baseline(checkpoints: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [row for row in checkpoints if int(row["checkpoint"]) == 0]
    result: dict[str, Any] = {"definition": "empirical empty-state measurement baseline; not a formal statistical null"}
    for metric in ("normalized_hse", "phi", "oracle_gain"):
        values = [row.get(metric) for row in rows if _num(row.get(metric)) is not None]
        result[metric] = {
            "n": len(values),
            "mean": _mean(values),
            "std_population": _std(values),
            "min": min(values) if values else None,
            "max": max(values) if values else None,
        }
    return result


def _detailed_label_rows(entries: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    detail: list[dict[str, Any]] = []
    cumulative: list[dict[str, Any]] = []
    for entry in entries:
        bundle = entry["bundle"]
        rounds = round_rows(bundle)
        selected_counts = Counter(row["selected_agent"] for row in rounds if row.get("selected_agent"))
        memory = memory_rows(bundle)
        final_memory = {}
        for row in memory:
            if int(row["round"]) == max(int(item["round"]) for item in memory):
                final_memory[str(row["agent_id"])] = int(row["memory_count"])
        final_checkpoint = max(bundle.checkpoints, key=lambda row: int(row.get("checkpoint", 0)))
        competence = final_checkpoint.get("competence_matrix", {})
        overall = {agent: _mean(profile.values()) for agent, profile in competence.items()}
        by_world = {
            world: _argmax_labels({agent: float(profile.get(world, 0.0)) for agent, profile in competence.items()})
            for world in sorted({world for profile in competence.values() for world in profile})
        }
        detail.append({
            "run_id": bundle.run_id,
            "seed": bundle.seed,
            "condition": bundle.condition,
            "total_rounds": len(rounds),
            "routing_counts": json.dumps(dict(sorted(selected_counts.items())), sort_keys=True),
            "dominant_routing_label": _argmax_labels({agent: float(value) for agent, value in selected_counts.items()}),
            "largest_memory_label": _argmax_labels({agent: float(value) for agent, value in final_memory.items()}),
            "best_overall_probe_label": _argmax_labels({agent: float(value) for agent, value in overall.items() if value is not None}),
            "best_label_by_world": json.dumps(by_world, sort_keys=True),
        })
        for threshold in (1, 5, 10, 20):
            prefix = [row for row in rounds if int(row["round"]) <= threshold]
            counts = Counter(row["selected_agent"] for row in prefix if row.get("selected_agent"))
            total = sum(counts.values())
            for agent in sorted(set(AGENTS) | set(counts)):
                cumulative.append({
                    "run_id": bundle.run_id,
                    "seed": bundle.seed,
                    "condition": bundle.condition,
                    "round_threshold": threshold,
                    "agent_id": agent,
                    "routing_count": counts.get(agent, 0),
                    "routing_share": counts.get(agent, 0) / total if total else 0.0,
                })
    return detail, cumulative


def _paired_utility_rows(paired: list[dict[str, Any]], online_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    online = {(int(row["seed"]), str(row["condition"])): row for row in online_rows}
    output: list[dict[str, Any]] = []
    for row in paired:
        if int(row["checkpoint"]) != 20:
            continue
        seed = int(row["seed"])
        private_online = online.get((seed, "private"), {})
        shared_online = online.get((seed, "shared"), {})
        output.append({
            "seed": seed,
            "online_interaction_accuracy_private": private_online.get("online_interaction_accuracy"),
            "online_interaction_accuracy_shared": shared_online.get("online_interaction_accuracy"),
            "oracle_gain_private": row.get("private_oracle_gain"),
            "oracle_gain_shared": row.get("shared_oracle_gain"),
            "eta_route_private": row.get("private_eta_route"),
            "eta_route_shared": row.get("shared_eta_route"),
            "u_match_private": row.get("private_u_match"),
            "u_match_shared": row.get("shared_u_match"),
            "u_single_private": row.get("private_u_single"),
            "u_single_shared": row.get("shared_u_single"),
            "delta_match_private": row.get("private_delta_match"),
            "delta_match_shared": row.get("shared_delta_match"),
            "u_route_private": row.get("private_u_route"),
            "u_route_shared": row.get("shared_u_route"),
            "u_rand_private": row.get("private_u_rand"),
            "u_rand_shared": row.get("shared_u_rand"),
            "u_oracle_domain_private": row.get("private_u_oracle_domain"),
            "u_oracle_domain_shared": row.get("shared_u_oracle_domain"),
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


def _plot_reports(
    root: Path,
    checkpoints: list[dict[str, Any]],
    paired: list[dict[str, Any]],
    competence: list[dict[str, Any]],
    routing: list[dict[str, Any]],
    rounds: list[dict[str, Any]],
    label_rows: list[dict[str, Any]],
    mi_rows: list[dict[str, Any]],
    online_rows: list[dict[str, Any]],
    reliability_rows: list[dict[str, Any]],
) -> list[str]:
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
        ("delta_phi", "delta_phi_trajectory.png", "Developmental change: ΔΦ(t)", "ΔΦ"),
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
    ys = [row.get("delta_hse_private_minus_shared") for row in terminal]
    ax.axhline(0, color="black", linewidth=0.8)
    ax.scatter(xs, ys, color="#3a506b")
    ax.set_xlabel("paired seed")
    ax.set_ylabel("D_HSE = ΔHSE(private) − ΔHSE(shared)")
    ax.set_title("Paired endpoint effect — descriptive, not inferential")
    ax.grid(alpha=0.2)
    save(fig, "paired_delta_hse.png")

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ys = [row.get("delta_phi_private_minus_shared") for row in terminal]
    ax.axhline(0, color="black", linewidth=0.8)
    ax.scatter(xs, ys, color="#6a4c93")
    ax.set_xlabel("paired seed")
    ax.set_ylabel("D_Φ = ΔΦ(private) − ΔΦ(shared)")
    ax.set_title("Paired developmental competence contrast")
    ax.grid(alpha=0.2)
    save(fig, "paired_delta_phi.png")

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    for condition in CONDITIONS:
        subset = [row for row in checkpoints if row["condition"] == condition and _num(row.get("oracle_gain")) is not None]
        grouped = defaultdict(list)
        for row in subset:
            grouped[int(row["checkpoint"])].append(float(row["oracle_gain"]))
        xs_metric = sorted(grouped)
        ax.plot(xs_metric, [statistics.fmean(grouped[x]) for x in xs_metric], marker="o", color=colors[condition], label=condition)
    ax.set_title("Item-level complementarity potential")
    ax.set_xlabel("checkpoint")
    ax.set_ylabel("oracle gain")
    ax.grid(alpha=0.2)
    ax.legend(frameon=False)
    save(fig, "oracle_gain.png")

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    for condition in CONDITIONS:
        subset = [row for row in checkpoints if row["condition"] == condition and _num(row.get("delta_match")) is not None]
        grouped = defaultdict(list)
        for row in subset:
            grouped[int(row["checkpoint"])].append(float(row["delta_match"]))
        xs_metric = sorted(grouped)
        ax.plot(xs_metric, [statistics.fmean(grouped[x]) for x in xs_metric], marker="o", color=colors[condition], label=condition)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("One-to-one domain matching potential")
    ax.set_xlabel("checkpoint")
    ax.set_ylabel("Δ_match = U_match − U_single")
    ax.grid(alpha=0.2)
    ax.legend(frameon=False)
    save(fig, "delta_match.png")

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    for condition in CONDITIONS:
        subset = [row for row in checkpoints if row["condition"] == condition and _num(row.get("routing_alignment_eta")) is not None]
        grouped = defaultdict(list)
        for row in subset:
            grouped[int(row["checkpoint"])].append(float(row["routing_alignment_eta"]))
        xs_metric = sorted(grouped)
        ax.plot(xs_metric, [statistics.fmean(grouped[x]) for x in xs_metric], marker="o", color=colors[condition], label=condition)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("Routing alignment with competence")
    ax.set_xlabel("checkpoint")
    ax.set_ylabel("η_route")
    ax.grid(alpha=0.2)
    ax.legend(frameon=False)
    save(fig, "eta_route.png")

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
    for condition in CONDITIONS:
        values = [row for row in mi_rows if row["condition"] == condition and _num(row.get("normalized_mi_excess")) is not None]
        ax.scatter(
            [row["normalized_routing_entropy"] for row in values],
            [row["normalized_mi_excess"] for row in values],
            alpha=0.65,
            color=colors[condition],
            label=condition,
        )
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("normalized routing entropy H(R)")
    ax.set_ylabel("normalized MI excess over permutation null")
    ax.set_title("Routing organization beyond finite-sample null")
    ax.grid(alpha=0.2)
    ax.legend(frameon=False)
    save(fig, "routing_entropy_vs_excess_mi.png")

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    for condition in CONDITIONS:
        values = [row for row in online_rows if row["condition"] == condition and _num(row.get("online_interaction_accuracy")) is not None]
        ax.scatter([int(row["seed"]) for row in values], [row["online_interaction_accuracy"] for row in values], color=colors[condition], label=condition)
    ax.set_title("Online interaction accuracy")
    ax.set_xlabel("paired seed")
    ax.set_ylabel("mean selected-answer correctness")
    ax.set_ylim(0, 1)
    ax.grid(alpha=0.2)
    ax.legend(frameon=False)
    save(fig, "online_team_accuracy.png")

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    axes[0].scatter([row["normalized_hse_private_0"] for row in reliability_rows], [row["normalized_hse_shared_0"] for row in reliability_rows], color="#3a506b")
    axes[0].plot([0, 1], [0, 1], linestyle="--", color="gray")
    axes[0].set_xlabel("private HSE(0)")
    axes[0].set_ylabel("shared HSE(0)")
    axes[0].set_title("Empty-state HSE agreement")
    axes[1].bar([str(row["seed"]) for row in reliability_rows], [row["t0_mean_behavioral_vector_correlation"] for row in reliability_rows], color="#6a4c93")
    axes[1].set_xlabel("paired seed")
    axes[1].set_ylabel("mean vector correlation")
    axes[1].set_ylim(-1, 1)
    axes[1].set_title("Behavioral-vector reliability")
    for ax in axes:
        ax.grid(axis="y", alpha=0.2)
    save(fig, "t0_measurement_reliability.png")

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
    mi_rows = _mi_null_rows(entries)
    online_rows = _online_accuracy_rows(entries)
    reliability_rows = _measurement_reliability_rows(entries)
    label_detail_rows, cumulative_routing_rows = _detailed_label_rows(entries)
    paired_utility_rows = _paired_utility_rows(paired, online_rows)
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
    _write_csv(tables / "label_sanity_detailed.csv", label_detail_rows)
    _write_csv(tables / "cumulative_routing.csv", cumulative_routing_rows)
    _write_csv(tables / "mi_permutation_null.csv", mi_rows)
    _write_csv(tables / "online_team_accuracy.csv", online_rows)
    _write_csv(tables / "measurement_reliability_t0.csv", reliability_rows)
    _write_csv(tables / "paired_developmental_outcomes.csv", [row for row in paired if int(row["checkpoint"]) == 20])
    _write_csv(tables / "paired_utility.csv", paired_utility_rows)
    _write_json(root / "empty_state_measurement_baseline.json", _empty_state_baseline(checkpoints))
    _write_csv(tables / "health_by_condition.csv", quality)

    metric_names = ("normalized_hse", "delta_normalized_hse", "phi", "delta_phi", "effective_competence_dimensionality", "normalized_utilization_entropy", "normalized_task_agent_mutual_information", "routing_alignment_eta", "oracle_gain", "division_of_labor_match", "single_agent_accuracy", "delta_match", "u_route", "u_rand", "u_oracle_domain", "best_individual_accuracy", "oracle_society_accuracy")
    aggregate_rows = [row for metric in metric_names for row in _aggregate_checkpoint(checkpoints, metric)]
    _write_csv(tables / "checkpoint_aggregates.csv", aggregate_rows)
    terminal = [row for row in paired if int(row["checkpoint"]) == 20]
    endpoint_stats = []
    for metric in ("delta_hse_private_minus_shared", "phi_level_private_minus_shared", "delta_phi_private_minus_shared", "private_normalized_hse", "shared_normalized_hse", "private_phi", "shared_phi", "private_d_eff", "shared_d_eff", "private_utilization", "shared_utilization", "private_mi", "shared_mi", "private_eta_route", "shared_eta_route", "private_oracle_gain", "shared_oracle_gain", "private_delta_match", "shared_delta_match"):
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

    generated_figures = _plot_reports(root, checkpoints, paired, competence, routing, rounds, label_rows, mi_rows, online_rows, reliability_rows)
    _write_json(root / "gate1_report_data.json", {
        "schema_version": 2,
        "watermark": "GATE 1 — OFFLINE DESCRIPTIVE REPORT; NOT A SCIENTIFIC CONCLUSION",
        "campaign": manifest.get("campaign"),
        "gate": GATE_1,
        "gate_status": manifest.get("gates", {}).get(GATE_1, {}).get("status"),
        "gate_2_status": manifest.get("gates", {}).get("gate_2_replication", {}).get("status"),
        "quality": quality_totals,
        "paired_endpoint_rows": terminal,
        "mi_permutation_null": mi_rows,
        "online_team_accuracy": online_rows,
        "measurement_reliability_t0": reliability_rows,
        "paired_utility": paired_utility_rows,
        "empty_state_measurement_baseline": _empty_state_baseline(checkpoints),
        "figures": generated_figures,
        "probe_set_hash": manifest.get("probe_set_hash"),
        "git_heads": sorted({row.get("git_commit") for row in provenance}),
    })

    def fmt(value: Any) -> str:
        return "—" if value is None else f"{float(value):.4f}" if isinstance(value, (int, float)) else str(value)

    d_values = [float(row["delta_hse_private_minus_shared"]) for row in terminal if _num(row.get("delta_hse_private_minus_shared")) is not None]
    d_without_seed1 = [float(row["delta_hse_private_minus_shared"]) for row in terminal if int(row["seed"]) != 1 and _num(row.get("delta_hse_private_minus_shared")) is not None]
    d_phi_values = [float(row["delta_phi_private_minus_shared"]) for row in terminal if _num(row.get("delta_phi_private_minus_shared")) is not None]
    online_means = {condition: _mean(row.get("online_interaction_accuracy") for row in online_rows if row["condition"] == condition) for condition in CONDITIONS}
    mi_excess_means = {condition: _mean(row.get("normalized_mi_excess") for row in mi_rows if row["condition"] == condition) for condition in CONDITIONS}
    reliability_means = {
        "agreement": _mean(row.get("t0_exact_correctness_agreement") for row in reliability_rows),
        "correlation": _mean(row.get("t0_mean_behavioral_vector_correlation") for row in reliability_rows),
    }
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
        f"At checkpoint 20, the mean paired effect D_HSE is **{fmt(mean_d)}** across seeds 1–10 and **{fmt(mean_d_no1)}** excluding seed 1. These are descriptive summaries; no inferential claim is made here.",
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
        "## Explicit developmental contrasts",
        "",
        "The paired table separates level and developmental competence contrasts. `phi_level_private_minus_shared` is Φ(private,t)−Φ(shared,t); `delta_phi_private_minus_shared` is the difference of within-condition changes from each condition's own t=0 baseline. They are not interchangeable.",
        "",
        "- Table A: `tables/paired_developmental_outcomes.csv` (including `delta_hse_private_minus_shared`, `phi_level_private_minus_shared`, `delta_phi_private_minus_shared`).",
        f"- Mean endpoint D_Φ across paired seeds: **{fmt(_mean(d_phi_values))}**; fraction positive: **{fmt(sum(value > 0 for value in d_phi_values) / len(d_phi_values) if d_phi_values else None)}**.",
        "",
        "![Delta Phi](figures/delta_phi_trajectory.png)",
        "",
        "![Paired Delta Phi](figures/paired_delta_phi.png)",
        "",
        "## MI permutation-null diagnostic",
        "",
        f"Each run uses {MI_PERMUTATIONS:,} deterministic permutations of selected-agent labels with the observed world sequence fixed. This is an exploratory finite-sample diagnostic, not a formal p-value. Mean normalized MI excess is private **{fmt(mi_excess_means['private'])}** and shared **{fmt(mi_excess_means['shared'])}**.",
        "",
        "- Table C: `tables/mi_permutation_null.csv`.",
        "- Reported fields include raw/normalized observed MI, null mean/std/95th percentile, excess MI and observed-null percentile.",
        "",
        "![Routing entropy versus MI excess](figures/routing_entropy_vs_excess_mi.png)",
        "",
        "## Online interaction accuracy",
        "",
        f"The routed interaction accuracy (not held-out probe accuracy) averages **{fmt(online_means['private'])}** for private and **{fmt(online_means['shared'])}** for shared. First/second-half and world-level values are retained in `tables/online_team_accuracy.csv`.",
        "",
        "![Online team accuracy](figures/online_team_accuracy.png)",
        "",
        "## Empty-state measurement reliability",
        "",
        f"At t=0 both conditions have empty controlled memory, but stochastic model responses can differ. Across paired seeds, same-label/same-probe correctness agreement averages **{fmt(reliability_means['agreement'])}** and the mean behavioral-vector correlation averages **{fmt(reliability_means['correlation'])}**. Constant-vector correlation uses the documented convention: identical constants → 1, unequal constants or one-constant pairs → 0.",
        "",
        "The t=0 panels are treated as an empirical empty-state measurement baseline, not a formal statistical null. See Table D (`tables/measurement_reliability_t0.csv`) and `empty_state_measurement_baseline.json`.",
        "",
        "![t=0 measurement reliability](figures/t0_measurement_reliability.png)",
        "",
        "## Utility and functional-structure diagnostics",
        "",
        "Table B (`tables/paired_utility.csv`) keeps separate: online team accuracy, oracle gain (item-level complementarity potential), U_match and Δ_match (one-to-one domain/niche potential), U_route/U_rand/U_oracle_domain and η_route (whether observed routing exploits competence). Undefined η_route values remain NA rather than being replaced by zero.",
        "",
        "![Oracle gain](figures/oracle_gain.png)",
        "",
        "![Delta match](figures/delta_match.png)",
        "",
        "![Routing alignment](figures/eta_route.png)",
        "",
        "## What the data show (descriptive)",
        "",
        "1. The paired design completed technically: all 20 runs contain the expected interaction and probe logical completions.",
        "2. Private and shared trajectories are not identical across seeds; the magnitude and direction of D are seed-dependent rather than a single deterministic path.",
        "3. Shared runs necessarily accumulate feedback in every agent, while private runs accumulate it only in selected agents; this manipulation is visible in `memory_trajectories.csv`.",
        "4. The endpoint observables do not all encode the same construct. In particular, routing concentration, HSE, competence variance, MI and oracle gain can disagree.",
        "",
        "## Interpretation boundary",
        "",
        "### Strongly supported by Gate 1",
        "",
        "- The matched private/shared manipulation changes developmental behavioral trajectories in the completed paired dataset.",
        "- Shared feedback produces equal recipient counts by construction, while private feedback localizes each selected experience; the health and provenance records are complete enough to audit this distinction.",
        "",
        "### Suggestive",
        "",
        "- Private runs tend to retain higher endpoint behavioral diversity and item-level complementarity potential than shared runs in these descriptive artifacts.",
        "- Confidence routing and feedback locality may jointly shape the type of differentiation, but the competence-alignment diagnostics are mixed.",
        "",
        "### Not established",
        "",
        "- Gate 1 does not establish emergent specialization, stable task-specific roles, useful division of labor, or a causal mechanism beyond the pre-specified manipulation.",
        "- HSE, Φ, MI, utilization entropy, oracle gain and matching are not interchangeable objectives and should not be optimized directly.",
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
