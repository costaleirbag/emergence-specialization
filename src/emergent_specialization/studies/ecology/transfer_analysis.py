"""Offline analysis for TRANSFER-GEOMETRY-CONTROL-V1.

This module consumes only the append-only geometry event logs.  It deliberately
keeps the measured transfer matrix separate from the effective toy dynamics:
the former is an empirical summary, while the latter is an explicitly stated
analysis model.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from emergent_specialization.studies.ecology.semantic_ecology import GEOMETRY_ECOLOGIES
from emergent_specialization.studies.ecology.transfer_geometry import DATA_ROOT, GEOMETRIES, REPORT_ROOT, SEEDS
from emergent_specialization.studies.ecology.transfer_operator import (centered_transfer, eigenvector_condition,
                                 geometry_metrics, numerical_abscissa,
                                 transient_amplification, toy_rhs)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({k for row in rows for k in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _terminal_events(geometry: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return all physical attempts and exactly one terminal observation/id."""
    path = DATA_ROOT / geometry.lower() / "events.jsonl"
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        grouped[event["logical_id"]].append(event)
    terminal: list[dict[str, Any]] = []
    for values in grouped.values():
        candidates = [event for event in values if event.get("error") is None or event.get("error_category") == "out_of_domain"]
        if candidates:
            terminal.append(sorted(candidates, key=lambda event: int(event.get("attempt", 0)))[-1])
    return events, terminal


def _accuracy_rows(geometry: str) -> list[dict[str, Any]]:
    _, terminal = _terminal_events(geometry)
    rows: list[dict[str, Any]] = []
    for event in terminal:
        task = event["task"]
        rows.append({
            "geometry": geometry,
            "seed": int(task["seed"]),
            "source": task.get("source") or "none",
            "target": task["target"],
            "h": int(task["h"]),
            "exposure_policy": task["exposure_policy"],
            "replicate": int(task["replicate"]),
            "case_id": task["case"]["case_id"],
            "correct": int(bool(event.get("correct"))),
            "ood": int(event.get("error_category") == "out_of_domain"),
            "retry_terminal": int(int(event.get("attempt", 0)) > 0),
        })
    return rows


def _mean_accuracy(rows: list[dict[str, Any]], *, seed: int, source: str, target: str,
                   h: int, policy: str, replicate: int | None = None) -> float:
    values = [row["correct"] for row in rows if row["seed"] == seed and row["source"] == source
              and row["target"] == target and row["h"] == h and row["exposure_policy"] == policy
              and (replicate is None or row["replicate"] == replicate)]
    if not values:
        raise ValueError(f"missing logical observations: {seed=} {source=} {target=} {h=} {policy=} {replicate=}")
    return float(statistics.mean(values))


def _matrix(rows: list[dict[str, Any]], geometry: str, seed: int, policy: str,
            replicate: int | None = None) -> np.ndarray:
    families = GEOMETRY_ECOLOGIES[geometry].families
    baseline = {target: _mean_accuracy(rows, seed=seed, source="none", target=target,
                                       h=0, policy="baseline", replicate=replicate)
                for target in families}
    values = np.zeros((len(families), len(families)), dtype=float)
    for i, source in enumerate(families):
        for j, target in enumerate(families):
            values[i, j] = _mean_accuracy(rows, seed=seed, source=source, target=target,
                                          h=8, policy=policy, replicate=replicate) - baseline[target]
    return values


def _diagonal_rows(rows: list[dict[str, Any]], geometry: str) -> list[dict[str, Any]]:
    families = GEOMETRY_ECOLOGIES[geometry].families
    result: list[dict[str, Any]] = []
    for seed in SEEDS:
        for family in families:
            baseline = _mean_accuracy(rows, seed=seed, source="none", target=family, h=0, policy="baseline")
            natural8 = _mean_accuracy(rows, seed=seed, source=family, target=family, h=8, policy="natural")
            teaching8 = _mean_accuracy(rows, seed=seed, source=family, target=family, h=8, policy="teaching")
            natural4 = _mean_accuracy(rows, seed=seed, source=family, target=family, h=4, policy="natural")
            teaching4 = _mean_accuracy(rows, seed=seed, source=family, target=family, h=4, policy="teaching")
            foreign = _mean_accuracy(rows, seed=seed, source=family, target=family, h=8, policy="foreign_theta")
            result.append({"geometry": geometry, "seed": seed, "family": family,
                           "baseline": baseline, "natural_h4": natural4, "natural_h8": natural8,
                           "teaching_h4": teaching4, "teaching_h8": teaching8,
                           "gap_D_h8": teaching8 - natural8, "gap_Q_h8": None,
                           "same_theta_natural_h8": natural8, "foreign_theta_h8": foreign,
                           "S_theta": natural8 - foreign})
    return result


def _alignment(geometry: str, policy: str, matrix: np.ndarray) -> dict[str, float | None]:
    G = np.asarray(GEOMETRY_ECOLOGIES[geometry].generate_environment(SEEDS[0]).metadata["designed_overlap"], dtype=float)
    off = ~np.eye(G.shape[0], dtype=bool)
    x, y = G[off], matrix[off]
    def rank(values: np.ndarray) -> np.ndarray:
        order = np.argsort(values, kind="stable")
        out = np.empty(len(values), dtype=float)
        out[order] = np.arange(1, len(values) + 1, dtype=float)
        return out
    rx, ry = rank(x), rank(y)
    spearman = float(np.corrcoef(rx, ry)[0, 1]) if np.std(rx) and np.std(ry) else 0.0
    P = np.eye(G.shape[0]) - np.ones_like(G) / G.shape[0]
    gx = P @ G @ P; lx = P @ matrix @ P
    den = float(np.linalg.norm(gx) * np.linalg.norm(lx))
    centered = float(np.sum(gx * lx) / den) if den else 0.0
    tg = centered_transfer(G); tl = centered_transfer(matrix)
    sg = np.sort(np.abs(np.linalg.eigvals(tg)))
    sl = np.sort(np.abs(np.linalg.eigvals(tl)))
    spec_den = float(np.linalg.norm(sg) * np.linalg.norm(sl))
    spectral = float(np.dot(sg, sl) / spec_den) if spec_den else 0.0
    return {"geometry": geometry, "exposure_policy": policy,
            "spearman_offdiag_G_L": spearman, "centered_frobenius_G_L": centered,
            "normalized_spectral_alignment": spectral}


def _bootstrap(values: list[float], *, seed: int, draws: int = 4000) -> tuple[float, float, float]:
    if not values:
        return (float("nan"), float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    sample = rng.choice(np.asarray(values, dtype=float), size=(draws, len(values)), replace=True).mean(axis=1)
    return float(np.mean(values)), float(np.quantile(sample, .025)), float(np.quantile(sample, .975))


def _stable_seed(*parts: object) -> int:
    payload = "|".join(map(str, parts)).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:4], "big")


def _toy_rows(geometry: str, policy: str, matrix: np.ndarray) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    N = K = 4; beta = gamma = 1.0
    initial = np.zeros((N, K), dtype=float); initial[0, 0] = 1e-4
    for kappa in (.25, .5, 1.0, 2.0, 4.0):
        eta = kappa * N * gamma / beta
        state = initial.copy(); norms: list[float] = []
        dt = .05
        for step in range(400):
            contrast = state - state.mean(axis=0, keepdims=True)
            norms.append(float(np.linalg.norm(contrast)))
            state += dt * toy_rhs(state, matrix, beta=beta, eta=eta, gamma=gamma)
        T = centered_transfer(matrix)
        J = kappa * T - np.eye(K)
        out.append({"geometry": geometry, "exposure_policy": policy, "kappa": kappa,
                    "linear_growth_rate": float(np.max(np.real(np.linalg.eigvals(J)))),
                    "initial_contrast": norms[0], "max_contrast": max(norms),
                    "final_contrast": norms[-1], "max_step": int(np.argmax(norms)),
                    "label": "EFFECTIVE TOY MODEL — NOT LLM SOCIETY DATA"})
    return out


def analyze() -> dict[str, Any]:
    all_metric_rows: list[dict[str, Any]] = []
    all_alignment_rows: list[dict[str, Any]] = []
    all_nonnormal_rows: list[dict[str, Any]] = []
    all_robust_rows: list[dict[str, Any]] = []
    all_toy_rows: list[dict[str, Any]] = []
    all_theta_rows: list[dict[str, Any]] = []
    all_cost_rows: list[dict[str, Any]] = []
    for geometry in GEOMETRIES:
        rows = _accuracy_rows(geometry)
        families = GEOMETRY_ECOLOGIES[geometry].families
        events, terminal = _terminal_events(geometry)
        ood = sum(row["ood"] for row in rows)
        retries = sum(int(event.get("attempt", 0)) > 0 for event in events)
        by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for event in events:
            by_id[event["logical_id"]].append(event)
        retry_categories = []
        for values in by_id.values():
            if len(values) > 1:
                retry_categories.extend(event.get("error_category") or event.get("error")
                                        for event in values
                                        if event.get("error") and event.get("error_category") != "out_of_domain")
        cost = sum(float(event.get("attempt_cost_usd") or 0.0) for event in events)
        all_cost_rows.append({"geometry": geometry, "physical_attempts": len(events), "logical_completions": len(terminal),
                              "technical_retries": retries, "semantic_ood": ood, "observed_cost_usd": cost,
                              "provider_models": ";".join(sorted({str(event.get("provider_metadata", {}).get("model")) for event in events})),
                              "retry_categories": ";".join(sorted({str(value) for value in retry_categories}))})
        for policy in ("natural", "teaching"):
            matrices = {seed: _matrix(rows, geometry, seed, policy) for seed in SEEDS}
            for seed, matrix in matrices.items():
                metric = geometry_metrics(matrix)
                metric.update({"geometry": geometry, "seed": seed, "exposure_policy": policy})
                all_metric_rows.append(metric)
            aggregate = np.mean(list(matrices.values()), axis=0)
            all_alignment_rows.append(_alignment(geometry, policy, aggregate))
            T = centered_transfer(aggregate)
            eig = np.linalg.eigvals(T)
            curve = transient_amplification(T, (0.0, .25, .5, 1.0, 2.0, 4.0))
            all_nonnormal_rows.append({"geometry": geometry, "exposure_policy": policy,
                                       "numerical_abscissa": numerical_abscissa(T),
                                       "max_real_eigenvalue": float(np.max(np.real(eig))),
                                       "eigenvector_condition": eigenvector_condition(T),
                                       "max_transient_amplification": max(row["amplification"] for row in curve),
                                       "transient_time_of_max": max(curve, key=lambda row: row["amplification"])["t"]})
            all_toy_rows.extend(_toy_rows(geometry, policy, aggregate))
            # Replicate and seed robustness: fixed replicate subsets expose
            # sensitivity to the two response draws without changing L_nat.
            for replicate in (0, 1):
                replicate_metrics = [geometry_metrics(_matrix(rows, geometry, seed, policy, replicate)) for seed in SEEDS]
                for metric_name in ("D", "O", "Q", "E_T", "chi", "r_eff", "A_dir"):
                    vals = [float(metric[metric_name]) for metric in replicate_metrics]
                    mean, low, high = _bootstrap(vals, seed=_stable_seed(geometry, policy, replicate, metric_name))
                    all_robust_rows.append({"geometry": geometry, "exposure_policy": policy, "analysis": "replicate_subset",
                                            "replicate": replicate, "metric": metric_name, "mean": mean,
                                            "ci95_low": low, "ci95_high": high})
            for held_out in SEEDS:
                loo = [matrices[seed] for seed in SEEDS if seed != held_out]
                loo_metric = geometry_metrics(np.mean(loo, axis=0))
                all_robust_rows.append({"geometry": geometry, "exposure_policy": policy, "analysis": "leave_one_seed_out",
                                        "held_out_seed": held_out, "metric": "Q", "mean": loo_metric["Q"]})
        theta_rows = _diagonal_rows(rows, geometry)
        all_theta_rows.extend(theta_rows)
        for metric_name in ("S_theta", "gap_D_h8"):
            vals = [float(row[metric_name]) for row in theta_rows if metric_name in row and row[metric_name] is not None]
            mean, low, high = _bootstrap(vals, seed=_stable_seed(geometry, metric_name))
            all_robust_rows.append({"geometry": geometry, "analysis": "seed_bootstrap", "metric": metric_name,
                                    "mean": mean, "ci95_low": low, "ci95_high": high})
    _write_csv(REPORT_ROOT / "transfer_metrics.csv", all_metric_rows)
    _write_csv(REPORT_ROOT / "alignment.csv", all_alignment_rows)
    _write_csv(REPORT_ROOT / "nonnormal_diagnostics.csv", all_nonnormal_rows)
    _write_csv(REPORT_ROOT / "toy_dynamics.csv", all_toy_rows)
    _write_csv(REPORT_ROOT / "robustness.csv", all_robust_rows)
    _write_csv(REPORT_ROOT / "theta_specificity_full.csv", all_theta_rows)
    _write_csv(REPORT_ROOT / "cost_audit.csv", all_cost_rows)
    return {"geometries": list(GEOMETRIES), "metrics": len(all_metric_rows), "status": "offline_analysis_complete"}


def main() -> None:
    parser = argparse.ArgumentParser(description="offline transfer-geometry analysis")
    parser.add_argument("--run", action="store_true", help="consume completed geometry event logs")
    args = parser.parse_args()
    if not args.run:
        parser.error("use --run; this command never performs model inference")
    print(json.dumps(analyze(), indent=2))


if __name__ == "__main__":
    main()
