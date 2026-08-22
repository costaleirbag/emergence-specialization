"""Measurement-aware, zero-call repair of the consumed clean V1.1 analysis.

This module deliberately lives beside (and never overwrites) the pre-measurement
mechanism decomposition.  It reuses read-only reconstruction helpers, creates
deterministic probe-half splits, and writes a separate measurement-aware report.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.stats import spearmanr

from emergent_specialization.studies.mechanisms.decomposition.analysis import (
    CHECKPOINTS_T,
    ECOLOGIES,
    INTERVALS,
    K,
    MACRO_CELLS_V11,
    MICRO,
    N,
    OUT as PREV_OUT,
    SOCIAL_SEEDS_V11,
    center,
    cosine,
    entropy,
    load_terminal_minimal,
    memory_features,
    metrics,
    pmat,
    reconstruct_trajectories,
    ridge_fit,
)
from emergent_specialization.studies.mechanisms.decomposition.analysis import checkpoint_competence
from emergent_specialization.studies.theory.v1.dynamics import psi_spec
from emergent_specialization.studies.theory.v1.micro_design import K_VALUES, double_swaps, single_swaps
from emergent_specialization.studies.theory.v1.micro_estimation import estimate_k_explicit, estimate_k_pairwise, superposition_diagnostics
from emergent_specialization.studies.theory.v1_1.replication import MICRO_SEEDS_V11
from emergent_specialization.studies.theory.v1_1.analysis import _bits, load_jsonl

ROOT = Path(__file__).resolve().parents[5]
V11 = ROOT / "data/auto-research/theory-v1-1"
MACRO_EVENTS = V11 / "macro/macro_events.jsonl"
MACRO_STEPS = V11 / "macro/macro_steps.jsonl"
STAGE_A = V11 / "stage_a_events.jsonl"
MACRO_CHECKPOINTS = V11 / "macro/macro_checkpoint_observations.jsonl"
OUT = ROOT / "reports/post-v1-measurement-aware"
NK = N * K
BOOTSTRAP_REPS = 2000


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _json_default(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    raise TypeError(type(value).__name__)


def corr(a: Sequence[float], b: Sequence[float], method: str = "pearson") -> float | None:
    x, y = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if len(x) < 2 or np.std(x) <= 1e-14 or np.std(y) <= 1e-14:
        return None
    if method == "spearman":
        return float(spearmanr(x, y).statistic)
    return float(np.corrcoef(x, y)[0, 1])


def _resolve_split_rows(probe_data: Mapping[tuple[str, int, str, int], Mapping[int, Mapping[int, list[dict[str, Any]]]]]) -> dict[tuple[str, int, str, int], dict[str, np.ndarray]]:
    """Split individual terminal probe rows by fixed odd/even probe index."""
    out: dict[tuple[str, int, str, int], dict[str, np.ndarray]] = {}
    for key, agents in probe_data.items():
        mats = {name: np.zeros((N, K), dtype=float) for name in ("bit_a", "bit_b", "joint_a", "joint_b")}
        for agent in range(N):
            for niche in range(K):
                rows = agents[agent][niche]
                halves = {0: [], 1: []}
                for row in rows:
                    probe_index = int(row["task"]["probe_index"])
                    halves[probe_index % 2].append(row)
                if len(halves[0]) != 4 or len(halves[1]) != 4:
                    raise AssertionError(f"probe-half denominator mismatch {key}/{agent}/{niche}")
                for parity, suffix in ((1, "a"), (0, "b")):
                    bit_values = [_bits(row) for row in halves[parity]]
                    mats[f"bit_{suffix}"][agent, niche] = float(np.mean(bit_values))
                    mats[f"joint_{suffix}"][agent, niche] = float(np.mean([bool(row["correct"]) for row in halves[parity]]))
        out[key] = mats
    return out


def reconstruct_split_matrices(terminal: Mapping[str, Mapping[str, Any]]) -> tuple[dict[tuple[str, int, str, int], dict[str, np.ndarray]], dict[tuple[str, int, str, int], dict[str, np.ndarray]]]:
    full, probe_data = checkpoint_competence(terminal)
    split = _resolve_split_rows(probe_data)
    for key, values in full.items():
        values.update(split[key])
    return full, split


def _sb(r: float | None) -> float | None:
    return None if r is None or r <= -0.999999 else float(2 * r / (1 + r))


def reliability_rows(matrices: Mapping[tuple[str, int, str, int], Mapping[str, np.ndarray]]) -> list[dict[str, Any]]:
    rows = []
    for (ec, seed, cid, t), m in sorted(matrices.items()):
        cell = next(c for c in MACRO_CELLS_V11 if str(c["cell_id"]) == cid)
        for construct in ("bit", "joint"):
            a, b = m[f"{construct}_a"], m[f"{construct}_b"]
            raw_r = corr(a.ravel(), b.ravel()); centered_r = corr(center(a).ravel(), center(b).ravel())
            rows.append({"ecology": ec, "seed": seed, "cell_id": cid, "beta": cell["beta"], "q_share": cell["q_share"], "checkpoint": t, "construct": construct, "pearson": raw_r, "centered_element_pearson": centered_r, "spearman": corr(a.ravel(), b.ravel(), "spearman"), "spearman_brown": _sb(raw_r), "role_geometry_cosine": cosine(center(a), center(b)), "same_checkpoint_specialist_agreement": float(np.mean(np.argmax(a, axis=0) == np.argmax(b, axis=0))), "niche_count": K})
    write_csv(OUT / "split_half_reliability.csv", rows)
    return rows


def _bootstrap_summary(values_by_seed: Mapping[int, float], rng: np.random.Generator) -> dict[str, Any]:
    values = np.asarray(list(values_by_seed.values()), dtype=float)
    if not len(values):
        return {"mean": None, "median": None, "bootstrap_lo": None, "bootstrap_hi": None, "seed_values": []}
    draws = np.asarray([np.mean(rng.choice(values, size=len(values), replace=True)) for _ in range(BOOTSTRAP_REPS)])
    return {"mean": float(np.mean(values)), "median": float(np.median(values)), "bootstrap_lo": float(np.quantile(draws, .025)), "bootstrap_hi": float(np.quantile(draws, .975)), "seed_values": values.tolist()}


def reliability_summary(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rng = np.random.default_rng(20260813)
    out = []
    for ec in ECOLOGIES:
        for construct in ("bit", "joint"):
            for checkpoint in CHECKPOINTS_T:
                sub = [r for r in rows if r["ecology"] == ec and r["construct"] == construct and int(r["checkpoint"]) == checkpoint]
                for metric_name in ("pearson", "centered_element_pearson", "spearman", "spearman_brown", "role_geometry_cosine", "same_checkpoint_specialist_agreement"):
                    vals = {int(r["seed"]): float(np.nanmean([float(x[metric_name]) for x in sub if int(x["seed"]) == int(r["seed"]) and x["cell_id"] == "C3"])) for r in sub if r["cell_id"] == "C3" and r[metric_name] is not None}
                    s = _bootstrap_summary(vals, rng)
                    out.append({"ecology": ec, "construct": construct, "checkpoint": checkpoint, "metric": metric_name, **s})
    write_csv(OUT / "split_half_reliability_summary.csv", out)
    return out


def crossfit_dynamics(matrices: Mapping[tuple[str, int, str, int], Mapping[str, np.ndarray]], full: Mapping[tuple[str, int, str, int], Mapping[str, np.ndarray]]) -> list[dict[str, Any]]:
    rows = []
    for (ec, seed, cid, end), current in sorted(matrices.items()):
        if end == 0:
            continue
        start = next(bounds[0] for bounds in INTERVALS if bounds[1] == end)
        previous = matrices[(ec, seed, cid, start)]; full0 = full[(ec, seed, cid, start)]["bit"]; full1 = full[(ec, seed, cid, end)]["bit"]
        za, zb = center(previous["bit_a"]), center(previous["bit_b"]); za1, zb1 = center(current["bit_a"]), center(current["bit_b"])
        ct = float(np.sum(za * zb)); ct1 = float(np.sum(za1 * zb1)); ctt_ab = float(np.sum(za * zb1)); ctt_ba = float(np.sum(zb * za1)); ctt = .5 * (ctt_ab + ctt_ba)
        psi_cross, psi_cross1 = ct / NK, ct1 / NK
        rein_cf = 2 * (ctt - ct) / NK; innov_cf = (ct1 + ct - 2 * ctt) / NK
        naive_z0, naive_dz = center(full0), center(full1 - full0)
        naive_rein = 2 * float(np.sum(naive_z0 * naive_dz)) / NK; naive_innov = float(np.sum(naive_dz * naive_dz)) / NK
        ab = 2 * (ctt_ab - ct) / NK; ba = 2 * (ctt_ba - ct) / NK
        cell = next(c for c in MACRO_CELLS_V11 if str(c["cell_id"]) == cid)
        # A cross-time cosine is only defined when both cross-half energy
        # estimates are positive and the resulting ratio is numerically sane.
        # Near-zero/negative finite-sample estimates are retained as raw
        # covariances above but are not reported as a role cosine.
        denom = math.sqrt(ct * ct1) if ct > 0 and ct1 > 0 else 0.0
        raw_role_cos = (ctt / denom) if denom > 1e-8 else None
        role_cos = raw_role_cos if raw_role_cos is not None and abs(raw_role_cos) <= 1.0 + 1e-8 else None
        rows.append({"ecology": ec, "seed": seed, "cell_id": cid, "beta": cell["beta"], "q_share": cell["q_share"], "interval_start": start, "interval_end": end, "psi_cross_start": psi_cross, "psi_cross_end": psi_cross1, "psi_cross_delta": psi_cross1 - psi_cross, "reinforcement_cf": rein_cf, "innovation_cf": innov_cf, "identity_error_cf": (psi_cross1 - psi_cross) - rein_cf - innov_cf, "reinforcement_cf_ab": ab, "reinforcement_cf_ba": ba, "ab_ba_disagreement": abs(ab - ba), "reinforcement_naive": naive_rein, "innovation_naive": naive_innov, "identity_error_naive": psi_spec(full1) - psi_spec(full0) - naive_rein - naive_innov, "role_cos_cf": role_cos, "role_cos_cf_raw": raw_role_cos, "role_cos_naive": cosine(naive_z0, center(full1)), "cf_measurement_unstable": abs(ab - ba) > .02})
    write_csv(OUT / "cross_fitted_dynamics.csv", rows)
    return rows


def crossfit_summary(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rng = np.random.default_rng(20260814); out = []
    for ec in ECOLOGIES:
        for cid in [str(c["cell_id"]) for c in MACRO_CELLS_V11]:
            for end in (16, 32, 64, 128):
                sub = [r for r in rows if r["ecology"] == ec and r["cell_id"] == cid and int(r["interval_end"]) == end]
                if not sub: continue
                for key in ("reinforcement_naive", "innovation_naive", "reinforcement_cf", "innovation_cf", "role_cos_cf", "ab_ba_disagreement"):
                    vals = {int(r["seed"]): float(r[key]) for r in sub if r[key] is not None}; s = _bootstrap_summary(vals, rng); out.append({"ecology": ec, "cell_id": cid, "interval_end": end, "metric": key, **s})
    write_csv(OUT / "cross_fitted_dynamics_summary.csv", out)
    return out


def construct_alignment(matrices: Mapping[tuple[str, int, str, int], Mapping[str, np.ndarray]], snapshots: Mapping[tuple[str, int, str, int], Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows, regret = [], []
    for (ec, seed, cid, t), snap in sorted(snapshots.items()):
        m = matrices[(ec, seed, cid, t)]; cell = next(c for c in MACRO_CELLS_V11 if str(c["cell_id"]) == cid); mu = snap["mu"]
        for construct in ("joint", "bit"):
            target = m[f"{construct}_a"] * .5 + m[f"{construct}_b"] * .5
            z_target, z_mu = center(target), center(mu)
            mu_best, target_best = np.argmax(mu, axis=0), np.argmax(target, axis=0)
            rows.append({"ecology": ec, "seed": seed, "cell_id": cid, "checkpoint": t, "beta": cell["beta"], "q_share": cell["q_share"], "construct": construct, "mae": float(np.mean(abs(mu - target))), "rmse": float(np.sqrt(np.mean((mu - target) ** 2))), "pearson": corr(mu.ravel(), target.ravel()), "spearman": corr(mu.ravel(), target.ravel(), "spearman"), "centered_cosine": cosine(z_mu, z_target), "top_agent_agreement": float(np.mean(mu_best == target_best)), "top2_agreement": float(np.mean([len(set(np.argsort(mu[:, n])[-2:]) & set(np.argsort(target[:, n])[-2:])) == 2 for n in range(K)]))})
            p_mu = np.column_stack([pmat(mu[:, n], float(cell["beta"]), float(cell["epsilon"])) for n in range(K)]).T
            p_target = np.column_stack([pmat(target[:, n], float(cell["beta"]), float(cell["epsilon"])) for n in range(K)]).T
            utility = lambda p: float(np.mean([np.dot(p[n], target[:, n]) for n in range(K)]))
            utility_bit = lambda p: float(np.mean([np.dot(p[n], m["bit_a"][:, n] * .5 + m["bit_b"][:, n] * .5) for n in range(K)]))
            regret.append({"ecology": ec, "seed": seed, "cell_id": cid, "checkpoint": t, "beta": cell["beta"], "q_share": cell["q_share"], "construct": construct, "U_p_mu": utility(p_mu), "U_p_target_oracle": utility(p_target), "U_random": float(np.mean(target)), "U_hard": float(np.mean(np.max(target, axis=0))), "belief_regret": utility(p_target) - utility(p_mu), "specialization_allocation_regret": utility_bit(p_target) - utility_bit(p_mu)})
    write_csv(OUT / "router_construct_alignment.csv", rows); write_csv(OUT / "router_regret_measurement_aware.csv", regret)
    return rows, regret


def joint_belief_oof(snapshots: Mapping[tuple[str, int, str, int], Mapping[str, Any]], matrices: Mapping[tuple[str, int, str, int], Mapping[str, np.ndarray]]) -> list[dict[str, Any]]:
    rows = []
    for (ec, seed, cid, t), snap in sorted(snapshots.items()):
        if t == 0: continue
        target = matrices[(ec, seed, cid, t)]["joint_a"] * .5 + matrices[(ec, seed, cid, t)]["joint_b"] * .5
        for a in range(N):
            for n in range(K):
                hist = snap["history"][a][n]; prior = 1 / 8
                vals = {"B0_cumulative": float(snap["mu"][a, n]), "B1_rolling4": float((sum(hist[-4:]) + 1) / (len(hist[-4:]) + 8)), "B2_rolling8": float((sum(hist[-8:]) + 1) / (len(hist[-8:]) + 8))}
                for decay in (.10, .25, .50, .75):
                    estimate = prior
                    for outcome in hist: estimate = decay * float(outcome) + (1 - decay) * estimate
                    vals[f"B3_EWMA_{decay:.2f}"] = estimate
                for model, value in vals.items(): rows.append({"ecology": ec, "seed": seed, "cell_id": cid, "checkpoint": t, "agent": a, "niche": n, "model": model, "estimate": value, "target_A_joint": float(target[a, n])})
    out = []
    for ec in ECOLOGIES:
        for held in SOCIAL_SEEDS_V11[ec]:
            for model in sorted({r["model"] for r in rows}):
                test = [r for r in rows if r["ecology"] == ec and int(r["seed"]) == int(held) and r["model"] == model]
                y = np.asarray([r["target_A_joint"] for r in test]); p = np.asarray([r["estimate"] for r in test]); out.append({"ecology": ec, "heldout_seed": held, "model": model, **metrics(y, p), "top_agent_agreement": None})
    write_csv(OUT / "joint_belief_oof.csv", out)
    return out


def random_private_crossfit(snapshots: Mapping[tuple[str, int, str, int], Mapping[str, Any]], matrices: Mapping[tuple[str, int, str, int], Mapping[str, np.ndarray]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    observations = []
    for ec in ECOLOGIES:
        for seed in SOCIAL_SEEDS_V11[ec]:
            for start, end in INTERVALS:
                s0, s1 = snapshots[(ec, seed, "C0", start)], snapshots[(ec, seed, "C0", end)]; m0, m1 = matrices[(ec, seed, "C0", start)], matrices[(ec, seed, "C0", end)]; exposure = s1["exposure"]
                for a in range(N):
                    for n in range(K):
                        own, foreign = float(exposure[a, n]), float(np.sum(exposure[a]) - exposure[a, n])
                        observations.append({"ecology": ec, "seed": seed, "interval_end": end, "agent": a, "niche": n, "own_exposure": own, "foreign_exposure": foreign, "baseline_a": float(m0["bit_a"][a, n]), "baseline_b": float(m0["bit_b"][a, n]), "future_a": float(m1["bit_a"][a, n]), "future_b": float(m1["bit_b"][a, n]), "future_joint_a": float(m1["joint_a"][a, n]), "future_joint_b": float(m1["joint_b"][a, n])})
    summaries = []
    rng = np.random.default_rng(20260815)
    for ec in ECOLOGIES:
        for end in (16, 32, 64, 128):
            sub = [r for r in observations if r["ecology"] == ec and int(r["interval_end"]) == end]
            for direction in ("A_to_B", "B_to_A"):
                ykey, bkey = (("future_b", "baseline_a") if direction == "A_to_B" else ("future_a", "baseline_b"))
                X = np.asarray([[1, r[bkey], r["own_exposure"], r["foreign_exposure"]] for r in sub]); y = np.asarray([r[ykey] for r in sub]); coef = np.linalg.lstsq(X, y, rcond=None)[0]
                seeds = sorted({int(r["seed"]) for r in sub}); draws = []
                for _ in range(BOOTSTRAP_REPS // 4):
                    sampled = rng.choice(seeds, size=len(seeds), replace=True); boot = [r for seed in sampled for r in sub if int(r["seed"]) == int(seed)]
                    xb = np.asarray([[1, r[bkey], r["own_exposure"], r["foreign_exposure"]] for r in boot]); yb = np.asarray([r[ykey] for r in boot]); draws.append(np.linalg.lstsq(xb, yb, rcond=None)[0][2])
                summaries.append({"ecology": ec, "interval_end": end, "direction": direction, "coef_intercept": coef[0], "coef_baseline": coef[1], "coef_own_exposure": coef[2], "coef_foreign_exposure": coef[3], "bootstrap_lo": float(np.quantile(draws, .025)), "bootstrap_hi": float(np.quantile(draws, .975)), "seed_count": len(seeds), "interpretation": "cross-half C0 ANCOVA; descriptive, seed-clustered"})
    write_csv(OUT / "random_private_crossfit_observations.csv", observations); write_csv(OUT / "random_private_crossfit_summary.csv", summaries)
    return observations, summaries


def memory_models_crossfit(snapshots: Mapping[tuple[str, int, str, int], Mapping[str, Any]], matrices: Mapping[tuple[str, int, str, int], Mapping[str, np.ndarray]]) -> list[dict[str, Any]]:
    data = []
    for (ec, seed, cid, t), snap in snapshots.items():
        if t == 0: continue
        m = matrices[(ec, seed, cid, t)]
        for a in range(N):
            for n in range(K): data.append({"ecology": ec, "seed": seed, "memory": snap["memory"][a], "target_a": float(m["bit_a"][a, n]), "target_b": float(m["bit_b"][a, n])})
    out = []
    for ec in ECOLOGIES:
        for held in SOCIAL_SEEDS_V11[ec]:
            train = [r for r in data if r["ecology"] == ec and int(r["seed"]) != int(held)]; test = [r for r in data if r["ecology"] == ec and int(r["seed"]) == int(held)]
            for model in ("M0", "M1", "M2", "M3"):
                X = np.asarray([memory_features(r["memory"], model, .5) for r in train]); Xt = np.asarray([memory_features(r["memory"], model, .5) for r in test]); y = np.asarray([r["target_a"] for r in train]); yt = np.asarray([r["target_b"] for r in test]); coef = ridge_fit(np.column_stack([np.ones(len(X)), X]), y); pred = np.column_stack([np.ones(len(Xt)), Xt]) @ coef
                out.append({"ecology": ec, "heldout_seed": held, "model": model, "target": "A_bit_cross_half", **metrics(yt, pred)})
    # M4 is deliberately retained as the already-registered tiny nonlinear
    # diagnostic, with its prior full-target OOF values copied as a sensitivity
    # reference rather than relabeled as a new fit.
    prior = PREV_OUT / "memory_model_oof.csv"
    if prior.exists():
        for row in csv.DictReader(prior.open(encoding="utf-8")):
            if row["model"] == "M4_tiny_tree": out.append({"ecology": row["ecology"], "heldout_seed": row["heldout_seed"], "model": "M4_tiny_tree", "target": "A_bit_full_prior_diagnostic", "mae": row["mae"], "rmse": row["rmse"], "r2": row["r2"], "spearman": row["spearman"], "n": row["n"]})
    write_csv(OUT / "memory_model_measurement_aware.csv", out)
    return out


def _micro_terminal_rows() -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in load_jsonl(MICRO): grouped[str(row["logical_id"])].append(row)
    rows = []
    for values in grouped.values():
        terminal = [r for r in values if r.get("terminal")]
        if len(terminal) != 1: raise AssertionError("MICRO terminal identity failure")
        r = terminal[0]; task = r["task"]; rows.append({**task, "correct": bool(r.get("decisions") == task["probe"]["y"]), "probe_index": int(task["probe_index"])})
    if len(rows) != 19584: raise AssertionError(f"MICRO terminal count {len(rows)}")
    return rows


def micro_k_audit() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = _micro_terminal_rows(); grouped = defaultdict(list)
    for r in rows: grouped[(r["ecology"], int(r["seed"]), int(r["k"]), int(r["state_index"]), int(r["probe_index"]) % 2)].append(r)
    stability, noise = [], []
    rng = np.random.default_rng(20260816)
    for ec in ECOLOGIES:
        for seed in MICRO_SEEDS_V11[ec]:
            for k in K_VALUES:
                halves = {}
                for parity in (0, 1):
                    base = np.asarray([np.mean([r["correct"] for r in grouped[(ec, seed, k, 0, parity)] if int(r["target"]) == target]) for target in range(K)])
                    responses, swaps = [], []
                    for index, swap in enumerate(single_swaps(seed, k)):
                        values = np.asarray([np.mean([r["correct"] for r in grouped[(ec, seed, k, index + 1, parity)] if int(r["target"]) == target]) for target in range(K)])
                        responses.append(values - base); delta = np.zeros(K); delta[int(swap["target"])] += 1; delta[int(swap["source"])] -= 1; swaps.append(delta)
                    halves[parity] = (estimate_k_explicit(swaps, responses), responses, base)
                ka, kb = halves[1][0], halves[0][0]
                eig_a = np.linalg.eigvals(ka); eig_b = np.linalg.eigvals(kb)
                stability.append({"ecology": ec, "seed": seed, "k": k, "K_half_A": json.dumps(ka.tolist()), "K_half_B": json.dumps(kb.tolist()), "cosine": cosine(ka, kb), "matrix_pearson": corr(ka.ravel(), kb.ravel()), "max_abs_difference": float(np.max(abs(ka - kb))), "max_real_eigenvalue_A": float(np.max(np.real(eig_a))), "max_real_eigenvalue_B": float(np.max(np.real(eig_b))), "eigenvalue_real_part_distance": float(np.linalg.norm(np.sort(np.real(eig_a)) - np.sort(np.real(eig_b))))})
                # Probe-noise sensitivity: fixed observed state probabilities,
                # no fitted trajectory; 200 deterministic Bernoulli draws.
                observed_r2 = []
                for parity in (0, 1):
                    obs, pred = [], []
                    for index, pair in enumerate(double_swaps(seed, k)):
                        state = 13 + index; actual = np.asarray([np.mean([r["correct"] for r in grouped[(ec, seed, k, state, parity)] if int(r["target"]) == target]) for target in range(K)]) - halves[parity][2]; left = single_swaps(seed, k).index(pair[0]); right = single_swaps(seed, k).index(pair[1]); obs.append(actual); pred.append(halves[parity][1][left] + halves[parity][1][right])
                    observed_r2.append(superposition_diagnostics(obs, pred)["r2"])
                null_r2 = []
                for _ in range(200):
                    parity = 1
                    base_sim = np.asarray([rng.binomial(4, np.mean([r["correct"] for r in grouped[(ec, seed, k, 0, parity)] if int(r["target"]) == target])) / 4 for target in range(K)])
                    sim_responses = []; sim_swaps = []
                    for index, swap in enumerate(single_swaps(seed, k)):
                        values = np.asarray([rng.binomial(4, np.mean([r["correct"] for r in grouped[(ec, seed, k, index + 1, parity)] if int(r["target"]) == target])) / 4 for target in range(K)])
                        sim_responses.append(values - base_sim); delta = np.zeros(K); delta[int(swap["target"])] += 1; delta[int(swap["source"])] -= 1; sim_swaps.append(delta)
                    sim_k = estimate_k_explicit(sim_swaps, sim_responses); sim_obs, sim_pred = [], []
                    for index, pair in enumerate(double_swaps(seed, k)):
                        state = 13 + index; actual = np.asarray([rng.binomial(4, np.mean([r["correct"] for r in grouped[(ec, seed, k, state, parity)] if int(r["target"]) == target])) / 4 for target in range(K)]) - base_sim; left = single_swaps(seed, k).index(pair[0]); right = single_swaps(seed, k).index(pair[1]); sim_obs.append(actual); sim_pred.append(sim_responses[left] + sim_responses[right])
                    null_r2.append(superposition_diagnostics(sim_obs, sim_pred)["r2"])
                noise.append({"ecology": ec, "seed": seed, "k": k, "observed_half_mean_r2": float(np.mean(observed_r2)), "noise_null_mean_r2": float(np.mean(null_r2)), "noise_null_q05": float(np.quantile(null_r2, .05)), "noise_null_q95": float(np.quantile(null_r2, .95)), "note": "200 deterministic Bernoulli half-probe simulations using observed state margins; methodological sensitivity only"})
    write_csv(OUT / "micro_k_half_stability.csv", stability); write_csv(OUT / "micro_double_swap_measurement_audit.csv", noise)
    return stability, noise


def sharing_timescale(memory_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for ec in ECOLOGIES:
        for cid, q, u in (("C3", 0.0, .25), ("C6", .5, .625), ("C7", 1.0, 1.0)):
            sub = [r for r in memory_rows if r["ecology"] == ec and r["cell_id"] == cid and int(r["checkpoint"]) == 128]
            rows.append({"ecology": ec, "cell_id": cid, "q_share": q, "u_expected": u, "fifo_k": 8, "expected_horizon_k_over_u": 8 / u, "observed_mean_age": float(np.mean([float(r["mean_age"]) for r in sub])), "observed_temporal_span": float(np.mean([float(r["temporal_span"]) for r in sub])), "observed_update_rate": float(np.mean([float(r["update_rate_per_global_task"]) for r in sub])), "observed_exact_case_overlap": float(np.mean([float(r.get("mean_pairwise_exact_case_overlap", 0.0)) for r in sub])), "interpretation": "timescale difference mechanically implied by update frequency; residual competence effect not identified"})
    write_csv(OUT / "sharing_timescale_measurement_aware.csv", rows); return rows


def attach_memory_overlap(memory_rows: Sequence[dict[str, Any]], snapshots: Mapping[tuple[str, int, str, int], Mapping[str, Any]]) -> None:
    """Attach exact case overlap reconstructed from immutable snapshots.

    ``reconstruct_trajectories`` intentionally leaves this derived diagnostic
    blank.  Computing it here from each checkpoint snapshot avoids silently
    importing the previous report's CSV and keeps the new analysis raw-led.
    """
    by_key = {(r["ecology"], int(r["seed"]), str(r["cell_id"]), int(r["checkpoint"])): [] for r in memory_rows}
    for key, snap in snapshots.items():
        memories = [set(int(item["uid"]) for item in snap["memory"][a]) for a in range(N)]
        overlaps = []
        for a in range(N):
            for b in range(a + 1, N):
                union = memories[a] | memories[b]
                overlaps.append(len(memories[a] & memories[b]) / len(union) if union else 1.0)
        value = float(np.mean(overlaps)) if overlaps else 1.0
        for row in memory_rows:
            if (row["ecology"], int(row["seed"]), str(row["cell_id"]), int(row["checkpoint"])) == key:
                row["mean_pairwise_exact_case_overlap"] = value


def measurement_adequacy(matrices: Mapping[tuple[str, int, str, int], Mapping[str, np.ndarray]]) -> list[dict[str, Any]]:
    rows = []
    for ec in ECOLOGIES:
        for construct in ("bit", "joint"):
            vals = np.asarray([m[f"{construct}_a"] for (e, _, _, t), m in matrices.items() if e == ec and t == 128]).ravel()
            variance = float(np.var(vals)); noise_factor = 3 if construct == "bit" else 1
            for probes in (8, 16, 32, 64, 128, 256):
                half_n = (probes / 2) * noise_factor; expected_noise = float(np.mean(vals * (1 - vals)) / max(half_n, 1)); reliability = variance / (variance + expected_noise) if variance + expected_noise > 0 else 0.0
                rows.append({"ecology": ec, "construct": construct, "probe_count_total": probes, "estimated_split_half_reliability": reliability, "method": "binomial variance extrapolation from observed half-state margins", "threshold_0_5": reliability >= .5, "threshold_0_7": reliability >= .7})
    write_csv(OUT / "measurement_adequacy_curve.csv", rows); return rows


def noise_subtracted_psi(matrices: Mapping[tuple[str, int, str, int], Mapping[str, np.ndarray]]) -> list[dict[str, Any]]:
    rows = []
    for (ec, seed, cid, t), m in sorted(matrices.items()):
        full = (m["bit_a"] + m["bit_b"]) / 2; cross = float(np.sum(center(m["bit_a"]) * center(m["bit_b"])) / NK); naive = float(psi_spec(full))
        p = np.clip(full, 0, 1); variance_term = float(np.mean(p * (1 - p) / 12.0))
        rows.append({"ecology": ec, "seed": seed, "cell_id": cid, "checkpoint": t, "psi_bit_naive": naive, "psi_bit_cross": cross, "psi_bit_noise_subtracted_sensitivity": naive - variance_term, "sampling_noise_term": variance_term})
    write_csv(OUT / "psi_measurement_aware.csv", rows); return rows


def psi_measurement_summary(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Seed-clustered summary of naive, cross-half, and sensitivity Psi."""
    out = []
    for ec in ECOLOGIES:
        for cid in [str(c["cell_id"]) for c in MACRO_CELLS_V11]:
            for t in CHECKPOINTS_T:
                sub = [r for r in rows if r["ecology"] == ec and r["cell_id"] == cid and int(r["checkpoint"]) == t]
                if not sub:
                    continue
                for metric in ("psi_bit_naive", "psi_bit_cross", "psi_bit_noise_subtracted_sensitivity"):
                    values = [float(r[metric]) for r in sub]
                    out.append({"ecology": ec, "cell_id": cid, "checkpoint": t, "metric": metric, "mean": float(np.mean(values)), "median": float(np.median(values)), "min": float(np.min(values)), "max": float(np.max(values)), "seed_count": len(values), "seed_values": json.dumps(values)})
    write_csv(OUT / "psi_measurement_summary.csv", out)
    return out


def joint_bit_relationship(matrices: Mapping[tuple[str, int, str, int], Mapping[str, np.ndarray]]) -> list[dict[str, Any]]:
    """Describe A_joint versus A_bit without imposing an independence law."""
    rows = []
    for (ec, seed, cid, t), m in sorted(matrices.items()):
        joint, bit = m["joint"], m["bit"]
        flat_joint, flat_bit = joint.ravel(), bit.ravel()
        cube_resid = flat_joint - flat_bit ** 3
        rows.append({"ecology": ec, "seed": seed, "cell_id": cid, "checkpoint": t, "pearson": corr(flat_joint, flat_bit), "spearman": corr(flat_joint, flat_bit, "spearman"), "mean_joint": float(np.mean(flat_joint)), "mean_bit": float(np.mean(flat_bit)), "mae_vs_bit_cube": float(np.mean(np.abs(cube_resid))), "rmse_vs_bit_cube": float(np.sqrt(np.mean(cube_resid ** 2))), "note": "descriptive; no bit-independence assumption"})
    write_csv(OUT / "joint_bit_relationship.csv", rows)
    return rows


def router_calibration_curves(snapshots: Mapping[tuple[str, int, str, int], Mapping[str, Any]], matrices: Mapping[tuple[str, int, str, int], Mapping[str, np.ndarray]]) -> list[dict[str, Any]]:
    """Fixed-bin mu -> A_joint calibration table, separated by regime."""
    rows = []
    edges = np.asarray([0.0, .2, .4, .6, .8, 1.0000001])
    for (ec, seed, cid, t), snap in sorted(snapshots.items()):
        target = matrices[(ec, seed, cid, t)]["joint"]
        mu = np.asarray(snap["mu"], dtype=float)
        for i in range(len(edges) - 1):
            mask = (mu >= edges[i]) & (mu < edges[i + 1])
            if not np.any(mask):
                continue
            y = target[mask]
            rows.append({"ecology": ec, "seed": seed, "cell_id": cid, "checkpoint": t, "beta": next(float(c["beta"]) for c in MACRO_CELLS_V11 if str(c["cell_id"]) == cid), "q_share": next(float(c["q_share"]) for c in MACRO_CELLS_V11 if str(c["cell_id"]) == cid), "bin_lo": edges[i], "bin_hi": edges[i + 1], "n": int(np.sum(mask)), "mean_mu": float(np.mean(mu[mask])), "mean_A_joint": float(np.mean(y)), "mae": float(np.mean(np.abs(mu[mask] - y)))})
    write_csv(OUT / "router_calibration_curves.csv", rows)
    return rows


def measurement_noise_null() -> list[dict[str, Any]]:
    # The latent matrices are fixed observed states only to set realistic
    # margins; no latent trajectory is fitted to the MACRO outcome.
    terminal, _ = load_terminal_minimal(); full, _ = reconstruct_split_matrices(terminal); rng = np.random.default_rng(20260817); rows = []
    representatives = [(ec, int(SOCIAL_SEEDS_V11[ec][0]), "C3") for ec in ECOLOGIES]
    for scenario in ("fixed_latent", "fixed_direction_magnitude", "small_role_rotation"):
        naive_r, naive_i, cf_r, cf_i = [], [], [], []
        for ec, seed, cid in representatives:
            base = full[(ec, seed, cid, 0)]["bit_a"] * .5 + full[(ec, seed, cid, 0)]["bit_b"] * .5; z = center(base)
            for _ in range(200):
                halves = {}
                for t in CHECKPOINTS_T:
                    scale = 1.0 if scenario == "fixed_latent" else (1 + .001 * t if scenario == "fixed_direction_magnitude" else 1.0)
                    latent = np.clip(.5 + scale * z, .05, .95)
                    if scenario == "small_role_rotation" and t >= 64: latent = latent[:, [1, 2, 3, 0]]
                    halves[t] = (rng.binomial(12, latent) / 12.0, rng.binomial(12, latent) / 12.0)
                for start, end in INTERVALS:
                    a0, b0 = center(halves[start][0]), center(halves[start][1]); a1, b1 = center(halves[end][0]), center(halves[end][1]); ct = np.sum(a0 * b0); ct1 = np.sum(a1 * b1); ctt = .5 * (np.sum(a0 * b1) + np.sum(b0 * a1)); naive_r.append(2 * np.sum(a0 * (a1 - a0)) / NK); naive_i.append(np.sum((a1 - a0) ** 2) / NK); cf_r.append(2 * (ctt - ct) / NK); cf_i.append((ct1 + ct - 2 * ctt) / NK)
        rows.append({"scenario": scenario, "naive_reinforcement_mean": float(np.mean(naive_r)), "naive_innovation_mean": float(np.mean(naive_i)), "crossfit_reinforcement_mean": float(np.mean(cf_r)), "crossfit_innovation_mean": float(np.mean(cf_i)), "replicates": len(naive_r), "interpretation": "methodological null; not LLM society data"})
    write_csv(OUT / "measurement_noise_null.csv", rows); return rows


def revised_evidence(cross_rows: Sequence[Mapping[str, Any]], reliability: Sequence[Mapping[str, Any]], alignment: Sequence[Mapping[str, Any]], memory_models: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    def mean(key, filt=lambda r: True):
        vals = [float(r[key]) for r in cross_rows if filt(r) and r.get(key) is not None]; return float(np.mean(vals)) if vals else None
    rel_bit = [float(r["role_geometry_cosine"]) for r in reliability if r["construct"] == "bit" and r["checkpoint"] == 128 and r["cell_id"] == "C3" and r["role_geometry_cosine"] is not None]
    rel_joint = [float(r["pearson"]) for r in reliability if r["construct"] == "joint" and r["checkpoint"] == 128 and r["cell_id"] == "C3" and r["pearson"] is not None]
    cf_rein = mean("reinforcement_cf"); naive_rein = mean("reinforcement_naive"); cf_innov = mean("innovation_cf"); naive_innov = mean("innovation_naive")
    out = {
        "H0_measurement_limited_dynamics": {"previous": "not_registered", "new": "MODERATE", "evidence": {"bit_role_cosine_mean": float(np.mean(rel_bit)), "joint_split_pearson_mean": float(np.mean(rel_joint)), "naive_reinforcement": naive_rein, "crossfit_reinforcement": cf_rein, "naive_innovation": naive_innov, "crossfit_innovation": cf_innov}, "caveat": "six clustered social seeds/ecology; diagnostic, not causal"},
        "H1_router_staleness": {"previous": "INCONCLUSIVE", "new": "INCONCLUSIVE", "evidence": "construct-corrected joint OOF is reported separately", "caveat": "A_joint reliability limits calibration"},
        "H2_selection_on_noise": {"previous": "INCONCLUSIVE", "new": "INCONCLUSIVE", "evidence": "beta/regret remains associational", "caveat": "no adaptive intervention"},
        "H3_exposure_memory_attenuation": {"previous": "INCONCLUSIVE", "new": "INCONCLUSIVE", "evidence": "cross-half C0 ANCOVA reported", "caveat": "limited seed count"},
        "H4_memory_state_insufficiency": {"previous": "INCONCLUSIVE", "new": "INCONCLUSIVE", "evidence": "cross-half M0-M3 plus prior M4 diagnostic", "caveat": "state-level targets remain noisy"},
        "H5_micro_macro_extrapolation": {"previous": "INCONCLUSIVE", "new": "INCONCLUSIVE", "evidence": "K half stability and distance audit", "caveat": "no direct causal transport test"},
        "H6_sharing_timescale": {"previous": "MODERATE", "new": "MODERATE", "evidence": "u(q) arithmetic predicts age/horizon shift", "caveat": "competence consequence not isolated"},
        "H7_differentiation_churn": {"previous": "INCONCLUSIVE", "new": "NON_IDENTIFIABLE", "evidence": "cross-fitted direction is reliability-limited", "caveat": "do not retain churn as robust mechanism"},
        "H8_multiple_bottlenecks": {"previous": "MODERATE", "new": "WEAK", "evidence": "several links remain imperfect but no causal closure decomposition", "caveat": "synthesis only"}
    }
    write_json(OUT / "revised_mechanism_evidence.json", out); return out


def make_figures(reliability: Sequence[Mapping[str, Any]], cross_rows: Sequence[Mapping[str, Any]], alignment: Sequence[Mapping[str, Any]], adequacy: Sequence[Mapping[str, Any]], evidence: Mapping[str, Any]) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return
    figdir = OUT / "figures"; figdir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 4))
    for ec in ECOLOGIES:
        x, y = [], []
        for t in CHECKPOINTS_T:
            vals = [float(r["role_geometry_cosine"]) for r in reliability if r["ecology"] == ec and r["construct"] == "bit" and r["checkpoint"] == t and r["cell_id"] == "C3" and r["role_geometry_cosine"] is not None]
            x.append(t); y.append(np.mean(vals) if vals else np.nan)
        ax.plot(x, y, marker="o", label=ec)
    ax.set_title("Split-half role-geometry reliability"); ax.set_xlabel("checkpoint"); ax.set_ylabel("cos(Z_a,Z_b)"); ax.legend(); fig.tight_layout(); fig.savefig(figdir / "role_geometry_reliability.png", dpi=140); plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4)); labels = []; nvals = []; cvals = []
    for ec in ECOLOGIES:
        for cid in ("C0", "C1", "C2", "C3", "C4", "C6", "C7"):
            sub = [r for r in cross_rows if r["ecology"] == ec and r["cell_id"] == cid and r["interval_end"] == 128]; labels.append(f"{ec[:3]}-{cid}"); nvals.append(np.mean([r["reinforcement_naive"] for r in sub])); cvals.append(np.mean([r["reinforcement_cf"] for r in sub]))
    xpos = np.arange(len(labels)); ax.bar(xpos - .18, nvals, .36, label="naive"); ax.bar(xpos + .18, cvals, .36, label="cross-fitted"); ax.axhline(0, color="black", linewidth=.6); ax.set_xticks(xpos); ax.set_xticklabels(labels, rotation=60, ha="right"); ax.legend(); ax.set_title("Reinforcement: naive vs cross-fitted"); fig.tight_layout(); fig.savefig(figdir / "naive_vs_crossfit_reinforcement.png", dpi=140); plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 4));
    for ec in ECOLOGIES:
        sub = [r for r in alignment if r["ecology"] == ec and r["construct"] == "joint"]
        ax.scatter([r["mae"] for r in sub], [r["centered_cosine"] if r["centered_cosine"] is not None else np.nan for r in sub], alpha=.25, label=ec)
    ax.set_xlabel("mu vs A_joint MAE"); ax.set_ylabel("centered cosine"); ax.legend(); ax.set_title("Router construct alignment"); fig.tight_layout(); fig.savefig(figdir / "mu_vs_joint_alignment.png", dpi=140); plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 4));
    for ec in ECOLOGIES:
        sub = [r for r in adequacy if r["ecology"] == ec and r["construct"] == "bit"]
        ax.plot([r["probe_count_total"] for r in sub], [r["estimated_split_half_reliability"] for r in sub], marker="o", label=ec)
    ax.axhline(.5, color="gray", linestyle="--"); ax.axhline(.7, color="black", linestyle=":"); ax.set_xscale("log", base=2); ax.set_xlabel("hypothetical total probes"); ax.set_ylabel("estimated split-half reliability"); ax.legend(); ax.set_title("Measurement adequacy extrapolation"); fig.tight_layout(); fig.savefig(figdir / "measurement_adequacy.png", dpi=140); plt.close(fig)
    fig, ax = plt.subplots(figsize=(6, 3)); names = list(evidence); values = [2 if evidence[n]["new"] == "MODERATE" else (1 if evidence[n]["new"] == "WEAK" else 0) for n in names]; ax.bar(names, values); ax.set_ylim(0, 2.4); ax.set_title("Revised mechanism evidence (developmental)"); fig.tight_layout(); fig.savefig(figdir / "revised_evidence.png", dpi=140); plt.close(fig)


def write_report(summary: Mapping[str, Any]) -> None:
    # The narrative report is a reviewed, provenance-bearing artifact.  Once
    # present, rerunning the deterministic numeric analysis must not silently
    # overwrite that reviewed text with a boilerplate rendering.
    report_path = ROOT / "docs/mechanisms/POST_V1_MEASUREMENT_AWARE_MECHANISM_REPORT.md"
    if report_path.exists():
        return
    report = f'''# Post-V1 measurement-aware mechanism repair

## Executive answer

The previous negative-reinforcement/positive-churn decomposition was algebraically
correct for the measured matrices but is not automatically a latent dynamical
decomposition. This repair separates `A_bit` (specialization) from `A_joint`
(the router's actual feedback target) and uses independent odd/even held-out
probe halves. The cross-fitted results and reliability ceilings are now the
primary mechanism evidence; the prior report remains preserved as a pre-
measurement-error analysis.

**Theory V1.1 remains prospectively NOT SUPPORTED.** This reanalysis does not
rescue it, revise it, or define Theory V2.

## Data integrity and provenance

Only clean V1.1 Stage A, MICRO, and canonical MACRO raws were used. External
calls: **0**; new cost: **US$0.00**. Raw hashes before/after are identical.
The canonical MACRO has 62,976 terminal logical observations from 62,995
physical attempts. Historical harness-confounded V1 and the quarantined serial
run were excluded. The registered plan and exact hashes are in
`reports/post-v1-measurement-aware/analysis_registry.json`.

## Measurement model and bias

With `Z_hat_t = Z_t + epsilon_t`, same-half naive reinforcement contains
`-2||epsilon_t||²` in expectation, while naive turnover contains positive
variance terms from both checkpoints. Thus an exact observed identity can have
biased components. Cross-fitting estimates latent cross-products using
independent probe halves and does not clip negative finite-sample values.

## Reliability and role geometry

The primary split is odd probe IDs versus even probe IDs. Reliability is reported
by ecology, seed, cell, checkpoint, and construct. Bit role-direction reliability
is measured by `cos(Z_bit^a,Z_bit^b)` and specialist identity agreement; joint
reliability is reported separately because it is the router construct.

## Naive versus cross-fitted dynamics

The exact naive decomposition is reproduced for validation. The cross-fitted
quantities are `Psi_cross`, cross-time covariance, `reinforcement_cf`, and
`innovation_cf`, with AB/BA disagreement exposed. The result must be read with
the reported reliability and six-seed uncertainty. The revised classification
does **not** retain “differentiation churn” as a robust mechanism; H7 is
measurement-limited/non-identifiable unless cross-fitted direction remains
stable.

## Router construct alignment

`mu` is calibrated primarily against `A_joint`, not `A_bit`. The report separates
calibration, ranking, and specialization relevance, and supplies joint-belief
regret plus secondary `mu`–`A_bit` association. OOF B0/rolling/EWMA diagnostics
use held-out social seeds. No router policy was changed.

## Exposure, memory, and plasticity

The C0 random-private analysis predicts future held-out `A_bit` from independent
baseline halves plus own/foreign exposure. This is the measurement-aware
cross-half/ANCOVA diagnostic, clustered by social seed, not an unrestricted
causal claim. M0–M4 remain a fixed ladder; no new memory representation was
searched.

## MICRO and sharing

K half-A/half-B stability and finite-probe double-swap sensitivity are reported
without fitting nonlinear alternatives. Sharing timescale is decomposed into
the mechanically expected update rate `u(q)` (`.25`, `.625`, `1.0` for q=`0`,
`.5`, `1`) and observed FIFO age/span/overlap. This prevents treating mechanical
turnover as an independently identified social mechanism.

## Revised mechanism evidence

H0 measurement-limited dynamics is a meta-diagnostic. H1 router staleness, H2
selection-on-noise, H3 exposure-memory attenuation, H4 memory-state insufficiency,
and H5 MICRO-to-MACRO extrapolation remain inconclusive. H6 sharing-timescale
remains moderate but is largely mechanically implied. H7 differentiation churn
is non-identifiable after the measurement correction. H8 is weakened to a weak
descriptive synthesis. Full evidence, caveats, and previous classifications are
in `revised_mechanism_evidence.json` and the CSV tables.

## What survives and what is withdrawn

Surviving claims are limited to: raw/state reconstruction is valid; `A_bit` and
`A_joint` are distinct constructs; probe reliability is a real ceiling; sharing
changes FIFO timescale/overlap; and cross-fitted diagnostics are required before
calling a directional mechanism. The strong pre-correction statement that
negative reinforcement demonstrates differentiation churn is withdrawn. The
previous report is not rewritten.

## Theory readiness and next step

Current measurements are not adequate for a trustworthy dynamical Theory V2.
The project should choose between a measurement-calibration-first design or an
empirical feedback-closure paper; no new experiment is authorized here. A draft
measurement calibration protocol is included only if the adequacy curve and
role reliability justify it. **NEXT ACTION: PRINCIPAL RESEARCHER REVIEW.**

## Outputs

- state/probe-half reliability tables;
- cross-fitted Delta-Psi dynamics and AB/BA sensitivity;
- measurement-noise null simulation;
- construct-aligned router calibration and regret;
- cross-half C0 plasticity;
- MICRO K stability and sharing-timescale arithmetic;
- measurement adequacy, revised evidence, figures, errata, and updated theory requirements.

Summary JSON: `reports/post-v1-measurement-aware/summary.json`.
'''
    report_path.write_text(report, encoding="utf-8")


def run() -> dict[str, Any]:
    raw_paths = (STAGE_A, MICRO, MACRO_EVENTS, MACRO_STEPS, MACRO_CHECKPOINTS)
    before = {str(path.relative_to(ROOT)): sha256(path) for path in raw_paths}
    terminal, health = load_terminal_minimal(); full, split = reconstruct_split_matrices(terminal); steps = load_jsonl(MACRO_STEPS); _, memory_rows, _, snapshots = reconstruct_trajectories(terminal, steps, full)
    rel = reliability_rows(full); reliability_summary(rel); cf = crossfit_dynamics(split, full); crossfit_summary(cf)
    align, regret = construct_alignment(full, snapshots); joint_belief_oof(snapshots, full); router_calibration_curves(snapshots, full); joint_bit_relationship(full); random_obs, random_sum = random_private_crossfit(snapshots, full); memory_models = memory_models_crossfit(snapshots, full); k_stability, k_noise = micro_k_audit(); attach_memory_overlap(memory_rows, snapshots); sharing = sharing_timescale(memory_rows); adequacy = measurement_adequacy(full); psi_rows = noise_subtracted_psi(full); psi_measurement_summary(psi_rows); null_rows = measurement_noise_null(); evidence = revised_evidence(cf, rel, align, memory_models); make_figures(rel, cf, align, adequacy, evidence)
    after = {str(path.relative_to(ROOT)): sha256(path) for path in raw_paths}
    if before != after: raise AssertionError("measurement-aware analysis changed raw data")
    summary = {"protocol": "POST-V1-MEASUREMENT-AWARE-MECHANISM-REPAIR", "external_model_calls": 0, "new_cost_usd": 0.0, "raw_hashes_before": before, "raw_hashes_after": after, "raw_hash_changes": 0, "macro_health": health, "reliability_rows": len(rel), "crossfit_rows": len(cf), "router_alignment_rows": len(align), "router_regret_rows": len(regret), "random_private_rows": len(random_obs), "memory_model_rows": len(memory_models), "micro_k_stability_rows": len(k_stability), "sharing_rows": len(sharing), "measurement_adequacy_rows": len(adequacy), "psi_rows": len(psi_rows), "noise_null_rows": len(null_rows), "evidence": evidence, "theory_v1_verdict_changed": False, "theory_v2_defined": False}
    write_json(OUT / "summary.json", summary); write_json(OUT / "raw_hash_manifest.json", {"protocol": summary["protocol"], "files": [{"path": k, "sha256": v} for k, v in before.items()], "before_after_equal": True, "external_model_calls": 0}); write_report(summary)
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True, default=_json_default))
