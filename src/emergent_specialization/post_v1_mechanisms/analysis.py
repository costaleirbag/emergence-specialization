"""Deterministic post-V1 mechanism decomposition.

The module is intentionally read-only with respect to scientific data.  It
reconstructs router and FIFO state from the canonical V1.1 online-step log,
joins held-out competence from terminal checkpoint completions, and writes
development diagnostics under ``reports/post-v1-mechanisms``.  It never creates
a provider or accesses credentials.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from scipy.stats import spearmanr

from ..theory_v1.dynamics import psi_spec
from ..theory_v1_1 import ECOLOGIES, MACRO_CELLS_V11, SOCIAL_SEEDS_V11
from ..theory_v1_1_analysis import _bits, _lid, load_jsonl

ROOT = Path(__file__).resolve().parents[3]
V11_DATA = ROOT / "data/auto-research/theory-v1-1"
MACRO = V11_DATA / "macro"
OUT = ROOT / "reports/post-v1-mechanisms"
STAGE_A = V11_DATA / "stage_a_events.jsonl"
MICRO = V11_DATA / "micro_events.jsonl"
MACRO_EVENTS = MACRO / "macro_events.jsonl"
MACRO_STEPS = MACRO / "macro_steps.jsonl"
CHECKPOINTS = MACRO / "macro_checkpoint_observations.jsonl"
CHECKPOINTS_T = (0, 16, 32, 64, 128)
INTERVALS = ((0, 16), (16, 32), (32, 64), (64, 128))
N = K = 4
MICRO_LOCAL_RADIUS = 2.0
ALPHAS = (0.10, 0.25, 0.50, 0.75)


def _default(x: Any) -> Any:
    if isinstance(x, np.ndarray): return x.tolist()
    if isinstance(x, (np.floating, np.integer)): return x.item()
    raise TypeError(type(x).__name__)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=_default) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    rows = list(rows); path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({k for row in rows for k in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        out = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        out.writeheader(); out.writerows(rows)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pmat(mu: Sequence[float], beta: float, epsilon: float) -> np.ndarray:
    values = np.asarray(mu, dtype=float); z = beta * values; z -= np.max(z)
    exp = np.exp(z); base = exp / exp.sum()
    return (1.0 - epsilon) * base + epsilon / N


def selected_from_p(probabilities: Sequence[float], u: float) -> int:
    cumulative = 0.0
    for i, value in enumerate(probabilities):
        cumulative += float(value)
        if float(u) < cumulative or i == len(probabilities) - 1:
            return i
    return len(probabilities) - 1


def center(x: Sequence[Sequence[float]]) -> np.ndarray:
    a = np.asarray(x, dtype=float); p_n = np.eye(a.shape[0]) - np.ones((a.shape[0], a.shape[0])) / a.shape[0]; p_k = np.eye(a.shape[1]) - np.ones((a.shape[1], a.shape[1])) / a.shape[1]
    return p_n @ a @ p_k


def cosine(a: np.ndarray, b: np.ndarray) -> float | None:
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if na <= 1e-14 or nb <= 1e-14: return None
    return float(np.sum(a * b) / (na * nb))


def corr(a: Sequence[float], b: Sequence[float], method: str = "pearson") -> float | None:
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if len(a) < 2 or np.std(a) <= 1e-14 or np.std(b) <= 1e-14: return None
    if method == "spearman": return float(spearmanr(a, b).statistic)
    return float(np.corrcoef(a, b)[0, 1])


def entropy(counts: Sequence[float]) -> float:
    x = np.asarray(counts, dtype=float); total = x.sum()
    if total <= 0: return 0.0
    p = x[x > 0] / total
    return float(-np.sum(p * np.log(p)) / math.log(len(x))) if len(x) > 1 else 0.0


def mutual_information(counts: Sequence[Sequence[float]]) -> float:
    """Mutual information of task niche and selected agent from a contingency."""
    table = np.asarray(counts, dtype=float)
    total = float(table.sum())
    if total <= 0:
        return 0.0
    p = table / total
    pi = p.sum(axis=1, keepdims=True)
    pj = p.sum(axis=0, keepdims=True)
    mask = p > 0
    terms = np.zeros_like(p)
    terms[mask] = p[mask] * np.log(p[mask] / (pi @ pj)[mask])
    return float(terms.sum())


def load_terminal_minimal() -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    physical = 0; model_set = set(); fingerprints = set()
    with MACRO_EVENTS.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip(): continue
            row = json.loads(line)
            if row.get("event") != "completion": continue
            physical += 1
            provider = row.get("provider_metadata") or {}
            if provider.get("model"): model_set.add(provider["model"])
            if provider.get("system_fingerprint"): fingerprints.add(provider["system_fingerprint"])
            if row.get("terminal"):
                task = row.get("task") or {}
                phase = "checkpoint" if task.get("checkpoint") in (0, 16, 32, 64, 128) else ("online" if task.get("role") == "online" else "other")
                # Keep only fields needed by diagnostics; the raw event remains immutable.
                grouped[str(row["logical_id"])].append({"ecology": row.get("ecology"), "task": task, "correct": bool(row.get("correct")), "decisions": row.get("decisions"), "expected": row.get("expected"), "phase": phase})
    terminal = {}
    for lid, rows in grouped.items():
        if len(rows) != 1: raise AssertionError(f"duplicate terminal logical id {lid}")
        terminal[lid] = rows[0]
    if len(terminal) != 62976: raise AssertionError(f"MACRO terminal coverage {len(terminal)}/62976")
    return terminal, {"physical_attempts": physical, "terminal": len(terminal), "models": sorted(model_set), "fingerprints": sorted(fingerprints)}


def checkpoint_competence(terminal: Mapping[str, Mapping[str, Any]]) -> tuple[dict[tuple[str, int, str, int], dict[str, np.ndarray]], dict[tuple[str, int, str, int], dict[int, dict[int, list[dict[str, Any]]]]]]:
    """Return full and split-half bit/joint competence plus probe rows."""
    grouped: dict[tuple[str, int, str, int, int, int], list[dict[str, Any]]] = defaultdict(list)
    probe_data: dict[tuple[str, int, str, int], dict[int, dict[int, list[dict[str, Any]]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for lid, row in terminal.items():
        task = row["task"]
        if task.get("checkpoint") not in CHECKPOINTS_T: continue
        ec, seed, niche = row["ecology"], int(task["seed"]), int(task["niche"])
        if task["checkpoint"] == 0:
            cell_ids = [str(c["cell_id"]) for c in MACRO_CELLS_V11]
            agent = None
        else:
            # Agent and cell are encoded in the logical ID; recover by matching the
            # frozen identity rather than relying on JSONL order.
            found = None
            for cell in MACRO_CELLS_V11:
                for a in range(N):
                    candidate = _lid("checkpoint", ec, seed, str(cell["cell_id"]), int(task["checkpoint"]), a, niche, int(task["probe_index"]))
                    if candidate == lid: found = (str(cell["cell_id"]), a); break
                if found: break
            if not found: continue
            cell_ids, agent = [found[0]], found[1]
        for cid in cell_ids:
            if agent is None:
                # t0 agent is likewise encoded in the common ID.
                for a in range(N):
                    candidate = _lid("t0", ec, seed, "COMMON_T0", 0, a, niche, int(task["probe_index"]))
                    if candidate == lid: agent = a; break
            if agent is None: raise AssertionError(f"unmatched t0 id {lid}")
            grouped[(ec, seed, cid, int(task["checkpoint"]), agent, niche)].append(row)
            probe_data[(ec, seed, cid, int(task["checkpoint"]))][agent][niche].append(row)
    matrices: dict[tuple[str, int, str, int], dict[str, np.ndarray]] = {}
    for ec in ECOLOGIES:
        for seed in SOCIAL_SEEDS_V11[ec]:
            for cell in MACRO_CELLS_V11:
                cid = str(cell["cell_id"])
                for t in CHECKPOINTS_T:
                    bit = np.zeros((N, K)); joint = np.zeros((N, K)); even = np.zeros((N, K)); odd = np.zeros((N, K))
                    for a in range(N):
                        for niche in range(K):
                            values = grouped[(ec, int(seed), cid, t, a, niche)]
                            if len(values) != 8: raise AssertionError(f"checkpoint denominator {ec}/{seed}/{cid}/{t}/{a}/{niche}: {len(values)}")
                            b = [_bits(v) for v in values]; bit[a, niche] = np.mean(b); joint[a, niche] = np.mean([v["correct"] for v in values])
                            even[a, niche] = np.mean([b[i] for i in range(0, 8, 2)])
                            odd[a, niche] = np.mean([b[i] for i in range(1, 8, 2)])
                    # Store exact joint and bit matrices. Split-half is computed component-wise later.
                    matrices[(ec, int(seed), cid, t)] = {"bit": bit, "joint": joint}
                    matrices[(ec, int(seed), cid, t)]["split_even"] = even
                    matrices[(ec, int(seed), cid, t)]["split_odd"] = odd
    return matrices, probe_data


def reconstruct_trajectories(terminal: Mapping[str, Mapping[str, Any]], step_rows: Sequence[Mapping[str, Any]], matrices: Mapping[tuple[str, int, str, int], Mapping[str, np.ndarray]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[tuple[str, int, str, int], dict[str, Any]]]:
    by_traj: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in step_rows:
        by_traj[(row["ecology"], int(row["seed"]), str(row["cell_id"]))].append(dict(row))
    state_rows: list[dict[str, Any]] = []; memory_rows: list[dict[str, Any]] = []; interval_rows: list[dict[str, Any]] = []; snapshots: dict[tuple[str, int, str, int], dict[str, Any]] = {}
    for ec in ECOLOGIES:
        for seed in SOCIAL_SEEDS_V11[ec]:
            for cell in MACRO_CELLS_V11:
                cid = str(cell["cell_id"]); steps = sorted(by_traj[(ec, int(seed), cid)], key=lambda x: int(x["t"]))
                if len(steps) != 128 or [int(x["t"]) for x in steps] != list(range(1, 129)): raise AssertionError(f"step coverage {ec}/{seed}/{cid}")
                alpha = np.ones((N, K)); beta_count = np.full((N, K), 7.0); memory: list[list[dict[str, Any]]] = [[] for _ in range(N)]; history: list[list[list[bool]]] = [[[] for _ in range(K)] for _ in range(N)]
                snap: dict[int, dict[str, Any]] = {0: {"alpha": alpha.copy(), "beta_count": beta_count.copy(), "mu": alpha/(alpha+beta_count), "memory": [list(x) for x in memory], "exposure": np.zeros((N,K)), "expected_exposure": np.zeros((N,K)), "history": [[list(v) for v in row] for row in history]}}
                # Include the empty initial state explicitly.  There is no
                # online task at t=0, so routing/task fields are null rather
                # than fabricated; held-out competence is attached later.
                mu0 = alpha / (alpha + beta_count)
                for a in range(N):
                    counts0 = [0] * K
                    for n in range(K):
                        p0 = pmat(mu0[:, n], float(cell["beta"]), float(cell["epsilon"]))
                        state_rows.append({"ecology": ec, "seed": int(seed), "cell_id": cid, "t": 0, "agent": a, "niche": n, "selected_agent": None, "task_niche": None, "correct": None, "alpha": float(alpha[a, n]), "beta_count": float(beta_count[a, n]), "mu": float(mu0[a, n]), "p_expected": float(p0[a]), "routing_u": None, "sharing_u_json": "[]", "recipients_json": "[]", "effective_sample_size": float(alpha[a, n] + beta_count[a, n]), "memory_count_niche": 0, "memory_entropy": 0.0, "oldest_age": None, "memory_size": 0, "memory_json": "[]"})
                interval_acc = {bounds: {"E": np.zeros((N,K)), "P": np.zeros((N,K))} for bounds in INTERVALS}
                for step in steps:
                    t, niche, selected = int(step["t"]), int(step["task"]["niche"]), int(step["selected_agent"]); mu_before = alpha[:, niche] / (alpha[:, niche] + beta_count[:, niche]); stored = np.asarray(step["mu_before"], dtype=float)
                    if np.max(np.abs(mu_before - stored)) > 1e-10: raise AssertionError(f"router posterior mismatch {ec}/{seed}/{cid}/{t}")
                    p_before = pmat(mu_before, float(cell["beta"]), float(cell["epsilon"]))
                    if selected_from_p(p_before, float(step["routing_u"])) != selected:
                        raise AssertionError(f"routing policy mismatch {ec}/{seed}/{cid}/{t}")
                    for bounds in INTERVALS:
                        if bounds[0] < t <= bounds[1]:
                            interval_acc[bounds]["E"][selected, niche] += 1.0; interval_acc[bounds]["P"][:, niche] += p_before
                    correct = bool(step["correct"]); recipients = [int(x) for x in step["recipients"]]
                    expected_recipients = [selected] + [a for a in range(N) if a != selected and float(step["sharing_u"][a]) < float(cell["q_share"])]
                    if recipients != expected_recipients: raise AssertionError(f"recipient mismatch {ec}/{seed}/{cid}/{t}")
                    if correct: alpha[selected, niche] += 1.0
                    else: beta_count[selected, niche] += 1.0
                    item = {"uid": t, "t": t, "niche": niche, "selected_agent": selected, "correct": correct, "x": step["task"].get("x"), "y": step["task"].get("y")}
                    for a in recipients:
                        memory[a].append(dict(item, provenance="selected" if a == selected else "shared"))
                        if len(memory[a]) > int(cell["k"]): del memory[a][:-int(cell["k"])]
                        history[a][niche].append(correct)
                    state_rows.extend(_state_rows(ec, int(seed), cid, cell, t, alpha, beta_count, memory, p_before, selected, niche, correct, step))
                    if t in CHECKPOINTS_T[1:]:
                        interval_key = next((bounds for bounds in INTERVALS if bounds[1] == t), None)
                        snap[t] = {"alpha": alpha.copy(), "beta_count": beta_count.copy(), "mu": alpha/(alpha+beta_count), "memory": [list(x) for x in memory], "history": [[list(v) for v in row] for row in history], "exposure": interval_acc[interval_key]["E"].copy() if interval_key else np.zeros((N,K)), "expected_exposure": interval_acc[interval_key]["P"].copy() if interval_key else np.zeros((N,K))}
                for t, value in snap.items():
                    snapshots[(ec, int(seed), cid, int(t))] = value
                    a = matrices[(ec, int(seed), cid, int(t))]["bit"]
                    updates_for_checkpoint = [0] * N
                    if t > 0:
                        interval_for_checkpoint = next((bounds for bounds in INTERVALS if bounds[1] == t), None)
                        if interval_for_checkpoint is not None:
                            for prior_step in steps:
                                pt = int(prior_step["t"])
                                if interval_for_checkpoint[0] < pt <= interval_for_checkpoint[1]:
                                    for recipient in prior_step["recipients"]:
                                        updates_for_checkpoint[int(recipient)] += 1
                    for agent in range(N):
                        mem = value["memory"][agent]; counts = [sum(int(item["niche"] == n) for item in mem) for n in range(K)]; ages = [t - int(item["t"]) for item in mem]; selected_slots = sum(item.get("provenance") == "selected" for item in mem); shared_slots = sum(item.get("provenance") == "shared" for item in mem)
                        memory_rows.append({"ecology": ec, "seed": int(seed), "cell_id": cid, "checkpoint": int(t), "agent": agent, "slot_count": len(mem), "niche_counts": json.dumps(counts), "memory_entropy": entropy(counts), "oldest_age": max(ages) if ages else None, "mean_age": float(np.mean(ages)) if ages else None, "temporal_span": (max(int(x["t"]) for x in mem)-min(int(x["t"]) for x in mem)) if mem else 0, "selected_slots": selected_slots, "shared_slots": shared_slots, "updates_since_previous_checkpoint": updates_for_checkpoint[agent], "update_rate_per_global_task": (updates_for_checkpoint[agent] / max(1, t - (next((bounds[0] for bounds in INTERVALS if bounds[1] == t), 0)))) if t > 0 else 0.0, "cross_agent_case_ids": ""})
                for bounds in INTERVALS:
                    start, end = bounds; start_snap, end_snap = snap[start], snap[end]; A0, A1 = matrices[(ec, int(seed), cid, start)]["bit"], matrices[(ec, int(seed), cid, end)]["bit"]; Z0, dZ = center(A0), center(A1 - A0); E, P = interval_acc[bounds]["E"], interval_acc[bounds]["P"]; M = np.zeros((N,K)); Mr = np.zeros((N,K))
                    for a in range(N):
                        for item in end_snap["memory"][a]:
                            M[a, int(item["niche"])] += 1
                            Mr[a, int(item["niche"])] += 0.75 ** max(0, end - int(item["t"]))
                    ZM, ZMr = center(M), center(Mr); Z_E, Z_P = center(E), center(P); Zmu = center(end_snap["mu"]); Rr = 2.0 * float(np.sum(Z0 * dZ)) / (N*K); Ri = float(np.sum(dZ*dZ)) / (N*K); dpsi = float(psi_spec(A1) - psi_spec(A0)); p_mu = np.zeros((N,K)); p_A = np.zeros((N,K))
                    for n in range(K): p_mu[:,n] = pmat(end_snap["mu"][:,n], float(cell["beta"]), float(cell["epsilon"])); p_A[:,n] = pmat(A1[:,n], float(cell["beta"]), float(cell["epsilon"]))
                    U_mu = float(np.mean([np.dot(p_mu[:,n], A1[:,n]) for n in range(K)])); U_A = float(np.mean([np.dot(p_A[:,n], A1[:,n]) for n in range(K)])); U_random = float(np.mean(A1)); U_hard = float(np.mean(np.max(A1, axis=0)))
                    actual_task_agent = E.T  # rows=niche, columns=agent
                    actual_selection_entropy = float(np.mean([entropy(actual_task_agent[n]) for n in range(K)]))
                    expected_selection_entropy = float(np.mean([entropy(p_mu[:, n]) for n in range(K)]))
                    mu_best = np.argmax(end_snap["mu"], axis=0); a_best = np.argmax(A1, axis=0)
                    winner_curse = float(np.mean([end_snap["mu"][mu_best[n], n] - A1[mu_best[n], n] for n in range(K)]))
                    selected_gap = float(np.mean([end_snap["mu"][mu_best[n], n] - np.mean(A1[:, n]) for n in range(K)]))
                    interval_rows.append({"ecology": ec, "seed": int(seed), "cell_id": cid, "beta": float(cell["beta"]), "q_share": float(cell["q_share"]), "interval_start": start, "interval_end": end, "norm_ZA_start": float(np.linalg.norm(Z0)), "norm_Delta_ZA": float(np.linalg.norm(dZ)), "norm_Zmu": float(np.linalg.norm(Zmu)), "norm_Zp": float(np.linalg.norm(Z_P)), "norm_ZE": float(np.linalg.norm(Z_E)), "norm_ZM": float(np.linalg.norm(ZM)), "norm_ZM_recency": float(np.linalg.norm(ZMr)), "reinforcement": Rr, "innovation": Ri, "delta_psi": dpsi, "identity_error": dpsi-(Rr+Ri), "cos_role_update": cosine(Z0,dZ), "C1_A_mu": cosine(Z0,Zmu), "C2_mu_p": cosine(Zmu,Z_P), "C3_p_E": cosine(Z_P,Z_E), "C4_E_M": cosine(Z_E,ZM), "C5_M_deltaA": cosine(ZM,dZ), "C_direct": cosine(Z0,dZ), "belief_regret": U_A-U_mu, "U_mu": U_mu, "U_A": U_A, "U_random": U_random, "U_hard": U_hard, "top_agent_agreement": float(np.mean(a_best==mu_best)), "mu_A_mae": float(np.mean(np.abs(end_snap["mu"]-A1))), "mu_A_brier": float(np.mean((end_snap["mu"]-A1)**2)), "actual_selection_entropy": actual_selection_entropy, "expected_selection_entropy": expected_selection_entropy, "task_agent_mutual_information": mutual_information(actual_task_agent), "exposure_residual_norm": float(np.linalg.norm(E-P)), "winner_curse_gap": winner_curse, "mu_selected_vs_mean_A": selected_gap, "mean_mu_effective_sample_size": float(np.mean(end_snap["alpha"]+end_snap["beta_count"]))})
    return state_rows, memory_rows, interval_rows, snapshots


def _state_rows(ec: str, seed: int, cid: str, cell: Mapping[str, Any], t: int, alpha: np.ndarray, beta_count: np.ndarray, memory: Sequence[Sequence[Mapping[str, Any]]], p_before: np.ndarray, selected: int, niche: int, correct: bool, step: Mapping[str, Any]) -> list[dict[str, Any]]:
    mu = alpha/(alpha+beta_count); rows=[]
    for a in range(N):
        counts = [sum(int(item["niche"] == n) for item in memory[a]) for n in range(K)]
        ages = [t-int(item["t"]) for item in memory[a]]
        memory_view = [{"uid": int(item["uid"]), "t": int(item["t"]), "niche": int(item["niche"]), "x": item.get("x"), "y": item.get("y"), "correct": bool(item.get("correct")), "provenance": item.get("provenance")} for item in memory[a]]
        for n in range(K):
            p = pmat(mu[:,n], float(cell["beta"]), float(cell["epsilon"]))
            rows.append({"ecology":ec,"seed":seed,"cell_id":cid,"t":t,"agent":a,"niche":n,"selected_agent":selected,"task_niche":niche,"correct":correct,"alpha":float(alpha[a,n]),"beta_count":float(beta_count[a,n]),"mu":float(mu[a,n]),"p_expected":float(p[a]),"routing_u":float(step.get("routing_u", float("nan"))),"sharing_u_json":json.dumps(step.get("sharing_u", []), sort_keys=True),"recipients_json":json.dumps(step.get("recipients", []), sort_keys=True),"effective_sample_size":float(alpha[a,n]+beta_count[a,n]),"memory_count_niche":counts[n],"memory_entropy":entropy(counts),"oldest_age":max(ages) if ages else None,"memory_size":len(memory[a]),"memory_json":json.dumps(memory_view, sort_keys=True, separators=(",", ":"))})
    return rows


def belief_estimators(snapshots: Mapping[tuple[str,int,str,int], Mapping[str,Any]], matrices: Mapping[tuple[str,int,str,int], Mapping[str,np.ndarray]]) -> list[dict[str,Any]]:
    rows=[]
    for (ec,seed,cid,t), snap in sorted(snapshots.items()):
        if t == 0: continue
        A = matrices[(ec,seed,cid,t)]["bit"]
        for a in range(N):
            for n in range(K):
                hist = snap["history"][a][n]; prior = 1/8
                vals = {"B0_cumulative": float(snap["mu"][a,n])}
                for k in (4,8): vals[f"B{k}_rolling"] = float((sum(hist[-k:])+1)/(len(hist[-k:])+8)) if hist else prior
                for decay in ALPHAS:
                    value = prior
                    for outcome in hist: value = decay*float(outcome)+(1-decay)*value
                    vals[f"B3_ewma_{decay:.2f}"] = value
                for name,value in vals.items(): rows.append({"ecology":ec,"seed":seed,"cell_id":cid,"checkpoint":t,"agent":a,"niche":n,"estimator":name,"estimate":value,"target_A_bit":float(A[a,n]),"effective_sample_size":float(snap["alpha"][a,n]+snap["beta_count"][a,n])})
    write_csv(OUT/"belief_estimators.csv", rows); return rows


def oof_belief(rows: Sequence[Mapping[str,Any]]) -> list[dict[str,Any]]:
    out=[]; models=sorted({r["estimator"] for r in rows})
    for ec in ECOLOGIES:
        for held in SOCIAL_SEEDS_V11[ec]:
            for model in models:
                train=[r for r in rows if r["ecology"]==ec and int(r["seed"])!=int(held) and r["estimator"]==model]; test=[r for r in rows if r["ecology"]==ec and int(r["seed"])==int(held) and r["estimator"]==model]
                if not test: continue
                y=np.asarray([r["target_A_bit"] for r in test]); pred=np.asarray([r["estimate"] for r in test]); out.append({"ecology":ec,"heldout_seed":held,"estimator":model,"mae":float(np.mean(np.abs(y-pred))),"rmse":float(np.sqrt(np.mean((y-pred)**2))),"r2":float(1-np.sum((y-pred)**2)/(np.sum((y-y.mean())**2) or 1)),"spearman":corr(y,pred,"spearman"),"n":len(test)})
    write_csv(OUT/"belief_oof.csv",out); return out


def memory_features(mem: Sequence[Mapping[str,Any]], model: str, decay: float = 0.5) -> np.ndarray:
    slots=list(mem)[-8:]; slots=[None]*(8-len(slots))+slots
    if model == "M0": return np.asarray([sum(int(x is not None and x["niche"]==n) for x in slots) for n in range(K)],float)
    if model == "M1": return np.asarray([sum((decay**(7-i))*int(x is not None and x["niche"]==n) for i,x in enumerate(slots)) for n in range(K)],float)
    pos=np.zeros((8,K))
    for i,x in enumerate(slots):
        if x is not None: pos[i,int(x["niche"])] = 1
    if model == "M2": return pos.ravel()
    pair=np.zeros((7,K,K))
    for i in range(7):
        if slots[i] is not None and slots[i+1] is not None: pair[i,int(slots[i]["niche"]),int(slots[i+1]["niche"])] = 1
    return np.concatenate([pos.ravel(),pair.ravel()])


def ridge_fit(X: np.ndarray,y: np.ndarray,lamb: float=1.0) -> np.ndarray:
    return np.linalg.solve(X.T@X+lamb*np.eye(X.shape[1]),X.T@y)


def metrics(y: np.ndarray,p: np.ndarray) -> dict[str,Any]:
    return {"mae":float(np.mean(np.abs(y-p))),"rmse":float(np.sqrt(np.mean((y-p)**2))),"r2":float(1-np.sum((y-p)**2)/(np.sum((y-y.mean())**2) or 1)),"spearman":corr(y,p,"spearman"),"n":len(y)}


def memory_model_oof(snapshots: Mapping[tuple[str,int,str,int], Mapping[str,Any]], matrices: Mapping[tuple[str,int,str,int], Mapping[str,np.ndarray]]) -> list[dict[str,Any]]:
    data=[]
    for (ec,seed,cid,t),snap in snapshots.items():
        if t==0: continue
        target=matrices[(ec,seed,cid,t)]["bit"]
        for a in range(N):
            for n in range(K): data.append({"ecology":ec,"seed":seed,"cell_id":cid,"checkpoint":t,"agent":a,"niche":n,"memory":snap["memory"][a],"target":float(target[a,n])})
    out=[]
    for ec in ECOLOGIES:
        for held in SOCIAL_SEEDS_V11[ec]:
            train=[r for r in data if r["ecology"]==ec and int(r["seed"])!=int(held)]; test=[r for r in data if r["ecology"]==ec and int(r["seed"])==int(held)]
            for model in ("M0","M1","M2","M3"):
                decay = 0.5
                if model == "M1":
                    # Select recency decay only inside the outer training
                    # fold, using leave-one-training-seed-out validation.
                    candidates = (0.25, 0.50, 0.75, 1.00); scores = []
                    train_seeds = sorted({int(r["seed"]) for r in train})
                    for candidate in candidates:
                        inner = []
                        for inner_held in train_seeds:
                            tr = [r for r in train if int(r["seed"]) != inner_held]; va = [r for r in train if int(r["seed"]) == inner_held]
                            Xi = np.asarray([memory_features(r["memory"], "M1", candidate) for r in tr])
                            Xv = np.asarray([memory_features(r["memory"], "M1", candidate) for r in va])
                            yi = np.asarray([r["target"] for r in tr])
                            yv = np.asarray([r["target"] for r in va])
                            coef = ridge_fit(np.column_stack([np.ones(len(Xi)), Xi]), yi)
                            pred_inner = np.column_stack([np.ones(len(Xv)), Xv]) @ coef
                            inner.append(float(np.mean(np.abs(yv - pred_inner))))
                        scores.append((float(np.mean(inner)), candidate))
                    decay = min(scores, key=lambda item: (item[0], item[1]))[1]
                X=np.asarray([memory_features(r["memory"],model,decay) for r in train]); Xt=np.asarray([memory_features(r["memory"],model,decay) for r in test]); y=np.asarray([r["target"] for r in train]); yt=np.asarray([r["target"] for r in test]); b=ridge_fit(np.column_stack([np.ones(len(X)),X]),y); p=np.column_stack([np.ones(len(Xt)),Xt])@b; out.append({"ecology":ec,"heldout_seed":held,"model":model,**metrics(yt,p),"parameter":decay if model=="M1" else None})
            # Deterministic tiny tree ceiling: a depth-2 recursive mean split.
            X=np.asarray([memory_features(r["memory"],"M3") for r in train]); Xt=np.asarray([memory_features(r["memory"],"M3") for r in test]); y=np.asarray([r["target"] for r in train]); yt=np.asarray([r["target"] for r in test]);
            pred=np.full(len(yt), y.mean())
            # Fit two deterministic stump splits on training residual reduction.
            nodes=[(np.arange(len(y)),0)]
            for idx in range(3):
                inds,depth=nodes.pop(0); best=None
                if depth>=2 or len(inds)<6: nodes.append((inds,depth)); continue
                for j in range(X.shape[1]):
                    vals=np.unique(X[inds,j]);
                    for threshold in vals[:-1]:
                        left=inds[X[inds,j]<=threshold]; right=inds[X[inds,j]>threshold]
                        if len(left)<3 or len(right)<3: continue
                        loss=np.sum((y[left]-y[left].mean())**2)+np.sum((y[right]-y[right].mean())**2)
                        if best is None or loss<best[0]: best=(loss,j,threshold,left,right)
                if best is None: nodes.append((inds,depth)); continue
                _,j,threshold,left,right=best
                for subset in (left,right): nodes.append((subset,depth+1))
                # assign predictions to all test rows reaching the same split path only for root; conservative ceiling
                mask=Xt[:,j]<=threshold; pred[mask]=y[left].mean(); pred[~mask]=y[right].mean()
            out.append({"ecology":ec,"heldout_seed":held,"model":"M4_tiny_tree","**metrics":None} if False else {"ecology":ec,"heldout_seed":held,"model":"M4_tiny_tree",**metrics(yt,pred),"parameter":"depth2"})
    write_csv(OUT/"memory_model_oof.csv",out); return out


def memory_model_cross_ecology(snapshots: Mapping[tuple[str,int,str,int], Mapping[str,Any]], matrices: Mapping[tuple[str,int,str,int], Mapping[str,np.ndarray]]) -> list[dict[str, Any]]:
    """Diagnostic transport: train one ecology, evaluate the other."""
    data = []
    for (ec, seed, cid, t), snap in snapshots.items():
        if t == 0:
            continue
        target = matrices[(ec, seed, cid, t)]["bit"]
        for a in range(N):
            for n in range(K):
                data.append({"ecology": ec, "seed": seed, "memory": snap["memory"][a], "target": float(target[a, n])})
    out = []
    for train_ec, test_ec in ((ECOLOGIES[0], ECOLOGIES[1]), (ECOLOGIES[1], ECOLOGIES[0])):
        train = [r for r in data if r["ecology"] == train_ec]
        test = [r for r in data if r["ecology"] == test_ec]
        for model in ("M0", "M1", "M2", "M3"):
            X = np.asarray([memory_features(r["memory"], model) for r in train]); Xt = np.asarray([memory_features(r["memory"], model) for r in test])
            y = np.asarray([r["target"] for r in train]); yt = np.asarray([r["target"] for r in test])
            coef = ridge_fit(np.column_stack([np.ones(len(X)), X]), y)
            pred = np.column_stack([np.ones(len(Xt)), Xt]) @ coef
            out.append({"train_ecology": train_ec, "test_ecology": test_ec, "model": model, **metrics(yt, pred)})
    write_csv(OUT / "memory_model_cross_ecology.csv", out)
    return out


def memory_order_ablation(snapshots: Mapping[tuple[str,int,str,int], Mapping[str,Any]], matrices: Mapping[tuple[str,int,str,int], Mapping[str,np.ndarray]]) -> list[dict[str, Any]]:
    """OOF count/order ablation; reverse is deterministic and preserves counts."""
    rows = []
    for ec in ECOLOGIES:
        for held in SOCIAL_SEEDS_V11[ec]:
            train, test = [], []
            for (row_ec, seed, cid, t), snap in snapshots.items():
                if row_ec != ec or t == 0:
                    continue
                target = matrices[(row_ec, seed, cid, t)]["bit"]
                bucket = test if int(seed) == int(held) else train
                for a in range(N):
                    for n in range(K):
                        mem = list(snap["memory"][a]); reversed_mem = list(reversed(mem))
                        bucket.append({"memory": mem, "reversed": reversed_mem, "target": float(target[a, n])})
            for feature_source in ("memory", "reversed"):
                X = np.asarray([memory_features(r[feature_source], "M2") for r in train]); Xt = np.asarray([memory_features(r[feature_source], "M2") for r in test])
                y = np.asarray([r["target"] for r in train]); yt = np.asarray([r["target"] for r in test]); coef = ridge_fit(np.column_stack([np.ones(len(X)), X]), y); pred = np.column_stack([np.ones(len(Xt)), Xt]) @ coef
                rows.append({"ecology": ec, "heldout_seed": held, "ablation": "ordered_slots" if feature_source == "memory" else "reversed_slots", **metrics(yt, pred)})
    write_csv(OUT / "memory_order_ablation_oof.csv", rows)
    return rows


def temporal_diagnostics(snapshots: Mapping[tuple[str,int,str,int], Mapping[str,Any]], matrices: Mapping[tuple[str,int,str,int], Mapping[str,np.ndarray]]) -> list[dict[str, Any]]:
    rows = []
    for ec in ECOLOGIES:
        for seed in SOCIAL_SEEDS_V11[ec]:
            for cid in [str(c["cell_id"]) for c in MACRO_CELLS_V11]:
                previous_a = previous_mu = None
                for t in CHECKPOINTS_T:
                    if t == 0:
                        previous_a = matrices[(ec, int(seed), cid, t)]["bit"]
                        previous_mu = snapshots[(ec, int(seed), cid, t)]["mu"]
                        continue
                    a = matrices[(ec, int(seed), cid, t)]["bit"]; mu = snapshots[(ec, int(seed), cid, t)]["mu"]
                    rows.append({"ecology": ec, "seed": int(seed), "cell_id": cid, "checkpoint": t, "A_autocorrelation": cosine(center(previous_a), center(a)), "mu_autocorrelation": cosine(center(previous_mu), center(mu)), "lagged_A_mu": cosine(center(previous_a), center(mu)), "A_change_norm": float(np.linalg.norm(center(a - previous_a))), "mu_change_norm": float(np.linalg.norm(center(mu - previous_mu)))})
                    previous_a, previous_mu = a, mu
    write_csv(OUT / "temporal_diagnostics.csv", rows)
    return rows


def negative_controls(snapshots: Mapping[tuple[str,int,str,int], Mapping[str,Any]], matrices: Mapping[tuple[str,int,str,int], Mapping[str,np.ndarray]]) -> list[dict[str, Any]]:
    """Deterministic label-permutation controls for centered alignment."""
    rows = []
    for (ec, seed, cid, t), snap in sorted(snapshots.items()):
        if t == 0:
            continue
        za = center(matrices[(ec, seed, cid, t)]["bit"]); zm = center(snap["mu"])
        rows.append({"ecology": ec, "seed": seed, "cell_id": cid, "checkpoint": t, "observed_A_mu": cosine(za, zm), "agent_reverse_null": cosine(za, center(snap["mu"][::-1, :])), "niche_reverse_null": cosine(za, center(snap["mu"][:, ::-1]))})
    write_csv(OUT / "negative_controls.csv", rows)
    return rows


def transportability(snapshots: Mapping[tuple[str,int,str,int], Mapping[str,Any]]) -> list[dict[str,Any]]:
    pred_path=ROOT/"reports/theory-v1-1/predictions/prediction_manifest.json"; pred={ (r["ecology"],r["cell_id"]):r for r in json.loads(pred_path.read_text())["prediction_rows"]}; growth_path=ROOT/"reports/theory-v1-1/macro/growth_by_seed.csv"; growth=list(csv.DictReader(growth_path.open()))
    rows=[]
    for key,snap in snapshots.items():
        ec,seed,cid,t=key; b=np.full(K,2); counts=np.asarray([[sum(int(x["niche"]==n) for x in snap["memory"][a]) for n in range(K)] for a in range(N)]); d=np.array([0.5*np.abs(counts[a]-b).sum() for a in range(N)]); rows.append({"ecology":ec,"seed":seed,"cell_id":cid,"checkpoint":t,"mean_d_swap":float(d.mean()),"max_d_swap":float(d.max()),"fraction_within_micro_radius":float(np.mean(d<=MICRO_LOCAL_RADIUS)),"outside_fraction":float(np.mean(d>MICRO_LOCAL_RADIUS))})
    # Add trajectory-level residual proxy where an observed growth and sealed prediction exist.
    for ec in ECOLOGIES:
        for seed in SOCIAL_SEEDS_V11[ec]:
            for cid in [str(c["cell_id"]) for c in MACRO_CELLS_V11]:
                subset=[r for r in rows if r["ecology"]==ec and int(r["seed"])==int(seed) and r["cell_id"]==cid and r["checkpoint"]>0]; g=next(r for r in growth if r["ecology"]==ec and r["seed"]==str(seed) and r["cell_id"]==cid); pr=pred[(ec,cid)]["g_excess_pred"]; residual=float(g["g_excess_obs"])-float(pr)
                for r in subset: r["g_excess_residual"] = residual
    write_csv(OUT/"transportability.csv",rows); return rows


def random_private_exposure_effect(snapshots: Mapping[tuple[str,int,str,int], Mapping[str,Any]], matrices: Mapping[tuple[str,int,str,int], Mapping[str,np.ndarray]]) -> list[dict[str,Any]]:
    """Associational C0 diagnostic: random allocation removes adaptive selection."""
    rows=[]
    for ec in ECOLOGIES:
        for seed in SOCIAL_SEEDS_V11[ec]:
            cid='C0'
            for start,end in INTERVALS:
                s0=snapshots[(ec,int(seed),cid,start)]; s1=snapshots[(ec,int(seed),cid,end)]; A0=matrices[(ec,int(seed),cid,start)]['bit']; A1=matrices[(ec,int(seed),cid,end)]['bit']; E=np.asarray(s1.get('exposure'),dtype=float)
                for a in range(N):
                    for n in range(K):
                        foreign=float(np.sum(E[a])-E[a,n]); rows.append({'ecology':ec,'seed':int(seed),'interval_start':start,'interval_end':end,'agent':a,'niche':n,'start_A':float(A0[a,n]),'delta_A':float(A1[a,n]-A0[a,n]),'own_exposure':float(E[a,n]),'foreign_exposure':foreign,'exposure_contrast':float(E[a,n]-foreign/(K-1))})
    write_csv(OUT/'random_private_exposure_competence.csv',rows)
    summaries=[]
    for ec in ECOLOGIES:
        sub=[r for r in rows if r['ecology']==ec]; X=np.asarray([[1,r['start_A'],r['own_exposure'],r['foreign_exposure']] for r in sub]); y=np.asarray([r['delta_A'] for r in sub]); coef=np.linalg.lstsq(X,y,rcond=None)[0]; summaries.append({'ecology':ec,'n_rows':len(sub),'coef_intercept':float(coef[0]),'coef_start_A':float(coef[1]),'coef_own_exposure':float(coef[2]),'coef_foreign_exposure':float(coef[3]),'cluster_unit':'ecology x social seed','interpretation':'associational C0 diagnostic; not a causal society estimate'})
    write_csv(OUT/'random_private_exposure_effect_summary.csv',summaries); return rows


def evidence(interval_rows: Sequence[Mapping[str,Any]], belief_oof_rows: Sequence[Mapping[str,Any]], model_rows: Sequence[Mapping[str,Any]], transport_rows: Sequence[Mapping[str,Any]]) -> list[dict[str,Any]]:
    def mean(key, filt=lambda r:True):
        x=[float(r[key]) for r in interval_rows if filt(r) and r.get(key) is not None]; return float(np.mean(x)) if x else None
    evidence_rows=[]
    # Fixed descriptive rules were registered as mechanism candidates; labels are not gates.
    rec={ec:np.mean([r["mae"] for r in belief_oof_rows if r["ecology"]==ec and r["estimator"]=="B0_cumulative"]) for ec in ECOLOGIES}; best={ec:min((np.mean([r["mae"] for r in belief_oof_rows if r["ecology"]==ec and r["estimator"]==m]),m) for m in sorted({r["estimator"] for r in belief_oof_rows})) for ec in ECOLOGIES}; rec_support=all(best[ec][0] < rec[ec]-0.005 for ec in ECOLOGIES)
    for h,claim,classification,support,contradiction in [
        ("H1","Cumulative belief may be stale relative to current FIFO competence", "MODERATE" if rec_support else "INCONCLUSIVE", f"best OOF MAE {best}", f"B0 OOF MAE {rec}"),
        ("H2","Higher beta may amplify posterior ranking error/one-step regret", "INCONCLUSIVE", "see belief_policy_regret by beta", "no preregistered causal intervention"),
        ("H3","Differential exposure may attenuate through FIFO memory", "INCONCLUSIVE", "see exposure/memory norms and C4", "adaptive exposure is associational"),
        ("H4","Counts may be insufficient; order/interactions may add held-out signal", "INCONCLUSIVE", "see M0-M4 OOF", "flexible models are diagnostic only"),
        ("H5","MICRO local K may extrapolate poorly to social memory states", "INCONCLUSIVE", "see d_swap and residual stratification", "growth residual is only a transport proxy"),
        ("H6","Sharing may change memory timescale as well as similarity", "MODERATE", "see q memory age/span/overlap", "q is not randomized across trajectories"),
        ("H7","Competence updates may churn rather than reinforce existing roles", "INCONCLUSIVE", "see reinforcement/innovation/cos_role_update", "finite checkpoint resolution"),
        ("H8","Several moderate transmission losses may jointly block closure", "MODERATE", "multiple links are reported separately", "not a fitted causal decomposition"),
    ]:
        evidence_rows.append({"hypothesis":h,"claim":claim,"classification":classification,"supporting_evidence":support,"contradicting_or_limit":contradiction,"uncertainty_unit":"ecology x social seed","causal_status":"developmental descriptive"})
    write_csv(OUT/"mechanism_evidence_table.csv", evidence_rows); return evidence_rows


def make_figures(interval_rows: Sequence[Mapping[str,Any]], memory_rows: Sequence[Mapping[str,Any]], model_rows: Sequence[Mapping[str,Any]], evidence_rows: Sequence[Mapping[str,Any]]) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return
    figdir=OUT/"figures"; figdir.mkdir(parents=True,exist_ok=True)
    # A→mu and signal chain.
    for name,key in (("signal_alignment","C1_A_mu"),("role_update","cos_role_update")):
        fig,ax=plt.subplots(figsize=(7,4));
        for ec in ECOLOGIES:
            vals=[]
            for t in (16,32,64,128):
                x=[float(r[key]) for r in interval_rows if r["ecology"]==ec and int(r["interval_end"])==t and r.get(key) is not None]
                vals.append(np.mean(x) if x else np.nan)
            ax.plot((16,32,64,128),vals,marker='o',label=ec)
        ax.set_xlabel('interval endpoint'); ax.set_ylabel(key); ax.legend(); fig.tight_layout(); fig.savefig(figdir/(name+'.png'),dpi=140); plt.close(fig)
    # Beta norms.
    fig,axes=plt.subplots(1,3,figsize=(12,3.5),sharex=True)
    for ec in ECOLOGIES:
        for j,key in enumerate(("norm_ZE","norm_ZM","norm_ZA_start")):
            x=[]; y=[]
            for beta in (0,4,8,12,20):
                vals=[float(r[key]) for r in interval_rows if r["ecology"]==ec and float(r["beta"])==beta and int(r["interval_end"])==128]
                x.append(beta); y.append(np.mean(vals) if vals else np.nan)
            axes[j].plot(x,y,marker='o',label=ec)
            axes[j].set_title(key); axes[j].set_xlabel('beta')
    axes[0].legend(); fig.tight_layout(); fig.savefig(figdir/'adaptive_norms.png',dpi=140); plt.close(fig)
    # q temporal span and memory diversity.
    fig,ax=plt.subplots(figsize=(7,4));
    for q in (0.0,0.5,1.0):
        vals=[float(r['mean_age']) for r in memory_rows if float(r.get('q_share',q))==q and r.get('mean_age') is not None] if memory_rows and 'q_share' in memory_rows[0] else []
        if not vals: vals=[float(r['mean_age']) for r in memory_rows if r['checkpoint']==128 and r['cell_id'] in ('C3','C6','C7') and ((q==0 and r['cell_id']=='C3') or (q==.5 and r['cell_id']=='C6') or (q==1 and r['cell_id']=='C7')) and r['mean_age'] is not None]
        ax.bar(str(q),np.mean(vals) if vals else 0)
    ax.set_title('Mean displayed memory age at endpoint'); fig.tight_layout(); fig.savefig(figdir/'sharing_memory_age.png',dpi=140); plt.close(fig)
    # Model ladder.
    fig,ax=plt.subplots(figsize=(7,4)); models=sorted({r['model'] for r in model_rows}); vals=[np.mean([float(r['r2']) for r in model_rows if r['model']==m]) for m in models]; ax.bar(models,vals); ax.set_ylabel('OOF R²'); ax.tick_params(axis='x',rotation=30); fig.tight_layout(); fig.savefig(figdir/'memory_models.png',dpi=140); plt.close(fig)
    # Evidence matrix.
    fig,ax=plt.subplots(figsize=(7,3)); cmap={'STRONG':3,'MODERATE':2,'WEAK':1,'INCONCLUSIVE':0,'CONTRADICTED':-1}; vals=np.asarray([[cmap.get(r['classification'],0)] for r in evidence_rows]); ax.imshow(vals,cmap='coolwarm',vmin=-1,vmax=3,aspect='auto'); ax.set_yticks(range(len(evidence_rows))); ax.set_yticklabels([r['hypothesis'] for r in evidence_rows]); ax.set_xticks([]); fig.tight_layout(); fig.savefig(figdir/'mechanism_evidence_matrix.png',dpi=140); plt.close(fig)
    # Exact Delta-Psi decomposition by ecology and interval.
    fig, ax = plt.subplots(figsize=(8, 4))
    labels = []
    for ec in ECOLOGIES:
        for end in (16, 32, 64, 128):
            sub = [r for r in interval_rows if r['ecology'] == ec and int(r['interval_end']) == end]
            labels.append(f"{ec.replace('_', '')}\n{end}")
            x = len(labels) - 1
            ax.bar(x - .16, float(np.mean([r['reinforcement'] for r in sub])), .30, color='#b2182b')
            ax.bar(x + .16, float(np.mean([r['innovation'] for r in sub])), .30, color='#2166ac')
    ax.axhline(0, color='black', linewidth=.6); ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, rotation=45, ha='right'); ax.set_ylabel('mean contribution'); ax.set_title('Delta-Psi: reinforcement vs innovation'); fig.tight_layout(); fig.savefig(figdir/'delta_psi_decomposition.png', dpi=140); plt.close(fig)
    # Compact causal-loop bottleneck summary; values are descriptive edge means.
    fig, ax = plt.subplots(figsize=(8, 3.5)); edges = ['A→mu', 'mu→p', 'p→E', 'E→M', 'M→ΔA']; keys = ['C1_A_mu', 'C2_mu_p', 'C3_p_E', 'C4_E_M', 'C5_M_deltaA']; xpos = np.arange(len(edges)); width=.35
    for j, ec in enumerate(ECOLOGIES):
        vals = [np.nanmean([float(r[key]) for r in interval_rows if r['ecology'] == ec and r.get(key) is not None]) for key in keys]
        ax.bar(xpos + (j - .5) * width, vals, width, label=ec)
    ax.axhline(0, color='black', linewidth=.6); ax.set_xticks(xpos); ax.set_xticklabels(edges); ax.set_ylabel('centered cosine'); ax.set_title('Signal-transmission diagnostic (not a causal gain)'); ax.legend(); fig.tight_layout(); fig.savefig(figdir/'causal_loop_bottlenecks.png', dpi=140); plt.close(fig)


def run() -> dict[str,Any]:
    raw_hashes={str(p.relative_to(ROOT)):sha256(p) for p in (STAGE_A,MICRO,MACRO_EVENTS,MACRO_STEPS,CHECKPOINTS)}
    terminal, health=load_terminal_minimal(); matrix, probes=checkpoint_competence(terminal); steps=load_jsonl(MACRO_STEPS)
    state_rows,memory_rows,interval_rows,snapshots=reconstruct_trajectories(terminal,steps,matrix)
    # Attach checkpoint observables to the otherwise event-level state panel.
    # Non-checkpoint rows retain empty values; no interpolation is performed.
    for row in state_rows:
        t = int(row["t"])
        if t in CHECKPOINTS_T:
            key = (row["ecology"], int(row["seed"]), str(row["cell_id"]), t)
            values = matrix[key]
            a, n = int(row["agent"]), int(row["niche"])
            row["A_bit_checkpoint"] = float(values["bit"][a, n])
            row["A_joint_checkpoint"] = float(values["joint"][a, n])
            row["Psi_bit_checkpoint"] = float(psi_spec(values["bit"]))
            row["Psi_joint_checkpoint"] = float(psi_spec(values["joint"]))
        else:
            row["A_bit_checkpoint"] = None
            row["A_joint_checkpoint"] = None
            row["Psi_bit_checkpoint"] = None
            row["Psi_joint_checkpoint"] = None
    random_private_exposure_effect(snapshots,matrix)
    # Attach q and exact overlap-friendly metadata to memory rows.
    params={(str(c['cell_id'])):c for c in MACRO_CELLS_V11}
    for row in memory_rows: row['beta']=params[row['cell_id']]['beta']; row['q_share']=params[row['cell_id']]['q_share']
    belief_rows=belief_estimators(snapshots,matrix); belief_oof_rows=oof_belief(belief_rows); model_rows=memory_model_oof(snapshots,matrix); memory_model_cross_ecology(snapshots,matrix); memory_order_ablation(snapshots,matrix); temporal_diagnostics(snapshots,matrix); negative_controls(snapshots,matrix); transport_rows=transportability(snapshots); evidence_rows=evidence(interval_rows,belief_oof_rows,model_rows,transport_rows)
    # Exact-case overlap and exposure tables are separate views of the same
    # reconstructed snapshots; they do not create new observations.
    for key, snap in snapshots.items():
        ec, seed, cid, t = key
        memories = [set(int(item['uid']) for item in snap['memory'][a]) for a in range(N)]
        overlaps = []
        for a in range(N):
            for b in range(a + 1, N):
                union = memories[a] | memories[b]
                overlaps.append(len(memories[a] & memories[b]) / len(union) if union else 1.0)
        for row in memory_rows:
            if row['ecology']==ec and int(row['seed'])==int(seed) and row['cell_id']==cid and int(row['checkpoint'])==int(t):
                row['mean_pairwise_exact_case_overlap'] = float(np.mean(overlaps)) if overlaps else 1.0
    write_csv(OUT/'state_panel.csv',state_rows); write_csv(OUT/'memory_dynamics.csv',memory_rows); write_csv(OUT/'signal_transmission.csv',interval_rows)
    write_csv(OUT/'routing_exposure.csv', [r for r in interval_rows if r['interval_end'] in (16,32,64,128)])
    write_csv(OUT/'delta_psi_decomposition.csv', [{k:r[k] for k in ('ecology','seed','cell_id','beta','q_share','interval_start','interval_end','delta_psi','reinforcement','innovation','identity_error','cos_role_update')} for r in interval_rows])
    write_csv(OUT/'belief_alignment.csv', [{k:r[k] for k in ('ecology','seed','cell_id','beta','q_share','interval_start','interval_end','C1_A_mu','C2_mu_p','C3_p_E','C4_E_M','C5_M_deltaA','C_direct','top_agent_agreement','mu_A_mae','mu_A_brier')} for r in interval_rows])
    # Delta-Psi identity and reliability tables.
    reliability=[]
    for (ec,seed,cid,t), values in matrix.items():
        if t==0: continue
        even,odd=values['split_even'],values['split_odd']; reliability.append({'ecology':ec,'seed':seed,'cell_id':cid,'checkpoint':t,'pearson_split_half':corr(even.ravel(),odd.ravel()),'spearman_split_half':corr(even.ravel(),odd.ravel(),'spearman'),'spearman_brown':(2*corr(even.ravel(),odd.ravel())/(1+corr(even.ravel(),odd.ravel())) if corr(even.ravel(),odd.ravel()) is not None and corr(even.ravel(),odd.ravel())>-0.99 else None)})
    write_csv(OUT/'reliability.csv',reliability)
    # Micro raw state summary and frozen linearity artifact.
    micro_rows=load_jsonl(MICRO); micro_summary=[]
    for row in micro_rows:
        if not row.get("terminal", True):
            continue
        task=row.get('task') or {}; bits=_bits(row); micro_summary.append({'ecology':task.get('ecology'),'seed':task.get('seed'),'k':task.get('k'),'state':task.get('state'),'target':task.get('target'),'joint_correct':bool(row.get('correct')),'bit_accuracy':float(np.mean(bits))})
    write_csv(OUT/'micro_controlled_summary.csv',micro_summary)
    linearity=ROOT/'reports/theory-v1-1/micro/linearity_diagnostics.csv'
    write_csv(OUT/'micro_linearity_reference.csv',list(csv.DictReader(linearity.open())))
    final_hashes={str(p.relative_to(ROOT)):sha256(p) for p in (STAGE_A,MICRO,MACRO_EVENTS,MACRO_STEPS,CHECKPOINTS)}
    if raw_hashes != final_hashes: raise AssertionError('raw hash changed during mechanism analysis')
    summary={'protocol':'POST-V1-MECHANISM-DECOMPOSITION','external_model_calls':0,'new_cost_usd':0.0,'raw_hashes_before':raw_hashes,'raw_hashes_after':final_hashes,'raw_hash_changes':0,'macro_health':health,'state_rows':len(state_rows),'memory_rows':len(memory_rows),'interval_rows':len(interval_rows),'reliability_rows':len(reliability),'belief_oof_rows':len(belief_oof_rows),'memory_model_rows':len(model_rows),'evidence':evidence_rows,'theory_v2_defined':False}
    write_json(OUT/'summary.json',summary); make_figures(interval_rows,memory_rows,model_rows,evidence_rows); return summary


if __name__ == '__main__':
    print(json.dumps(run(),indent=2,sort_keys=True,default=_default))
