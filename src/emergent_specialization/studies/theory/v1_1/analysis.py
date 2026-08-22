"""Offline analysis for the completed Theory V1.1 MACRO campaign.

This module consumes only the immutable V1.1 raw event logs.  It never creates
provider clients and never makes external calls.  The checkpoint side-journal
is treated as an auxiliary index: competence is reconstructed from terminal
completion events, so resumptions cannot silently remove observations.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
from scipy.stats import spearmanr

from emergent_specialization.studies.theory.v1.dynamics import psi_spec
from emergent_specialization.studies.theory.v1_1.replication import ECOLOGIES, MACRO_CELLS_V11, SOCIAL_SEEDS_V11, stable_hash

ROOT = Path(__file__).resolve().parents[5]
REPORT = ROOT / "reports/theory-v1-1"
DATA = ROOT / "data/auto-research/theory-v1-1/macro"
EVENTS = DATA / "macro_events.jsonl"
CHECKPOINTS = DATA / "macro_checkpoint_observations.jsonl"
EXPECTED_LOGICAL = 62976
N = K = 4
CHECKPOINT_VALUES = (0, 16, 32, 64, 128)


def _lid(phase: str, ecology: str, seed: int, cell_id: str, checkpoint: int, agent: int, niche: int, probe: int | None = None, t: int | None = None) -> str:
    """V1.1 logical identity (the legacy runner's global protocol is V1)."""
    return stable_hash({"protocol": "THEORY-V1.1", "phase": phase, "ecology": ecology, "seed": seed, "cell": cell_id, "checkpoint": checkpoint, "agent": agent, "niche": niche, "probe": probe, "t": t})


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=_default) + "\n", encoding="utf-8")


def _default(x: Any) -> Any:
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (np.floating, np.integer)):
        return x.item()
    raise TypeError(type(x).__name__)


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        out = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        out.writeheader(); out.writerows(rows)


def _bits(event: Mapping[str, Any]) -> list[bool]:
    decisions, expected = event.get("decisions"), event.get("expected")
    if not isinstance(decisions, list) or not isinstance(expected, list) or len(decisions) != 3 or len(expected) != 3:
        return [False, False, False]
    return [a == b for a, b in zip(decisions, expected)]


def expected_checkpoint_ids() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for ecology in ECOLOGIES:
        for seed in SOCIAL_SEEDS_V11[ecology]:
            for cell in MACRO_CELLS_V11:
                cid = str(cell["cell_id"])
                for checkpoint in CHECKPOINT_VALUES[1:]:
                    for agent in range(N):
                        for niche in range(K):
                            for probe in range(8):
                                lid = _lid("checkpoint", ecology, int(seed), cid, checkpoint, agent, niche, probe)
                                result[lid] = {"ecology": ecology, "seed": int(seed), "cell_id": cid, "checkpoint": checkpoint, "agent": agent, "niche": niche, "probe_index": probe}
    return result


def expected_t0_ids() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for ecology in ECOLOGIES:
        for seed in SOCIAL_SEEDS_V11[ecology]:
            for agent in range(N):
                for niche in range(K):
                    for probe in range(8):
                        lid = _lid("t0", ecology, int(seed), "COMMON_T0", 0, agent, niche, probe)
                        result[lid] = {"ecology": ecology, "seed": int(seed), "cell_id": "COMMON_T0", "checkpoint": 0, "agent": agent, "niche": niche, "probe_index": probe}
    return result


def terminal_events() -> dict[str, dict[str, Any]]:
    rows = load_jsonl(EVENTS)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("event") == "completion":
            grouped[str(row["logical_id"])].append(row)
    terminal: dict[str, dict[str, Any]] = {}
    for lid, values in grouped.items():
        finals = [row for row in values if row.get("terminal")]
        if len(finals) != 1:
            raise AssertionError(f"logical_id {lid} terminal count={len(finals)}")
        terminal[lid] = finals[0]
    if len(terminal) != EXPECTED_LOGICAL:
        raise AssertionError(f"terminal coverage {len(terminal)}/{EXPECTED_LOGICAL}")
    if len({row.get("logical_id") for row in terminal.values()}) != EXPECTED_LOGICAL:
        raise AssertionError("duplicate terminal logical IDs")
    return terminal


def reconstruct_checkpoint_aux(terminal: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    expected = expected_checkpoint_ids()
    present = {str(row["logical_id"]) for row in load_jsonl(CHECKPOINTS)}
    missing = sorted(set(expected) - present)
    unexpected = sorted(present - set(expected))
    rows = []
    raw_sha = hashlib.sha256(EVENTS.read_bytes()).hexdigest()
    raw_lines = EVENTS.read_text(encoding="utf-8").splitlines()
    line_by_id = {str(json.loads(line).get("logical_id")): i for i, line in enumerate(raw_lines, 1) if line.strip()}
    for lid in missing:
        meta = expected[lid]; event = terminal.get(lid)
        if event is None:
            raise AssertionError(f"missing raw terminal for {lid}")
        task = event.get("task") or {}
        if int(task.get("checkpoint", -1)) != meta["checkpoint"]:
            raise AssertionError(f"task/checkpoint mismatch {lid}")
        rows.append({"logical_id": lid, **meta, "correct": bool(event.get("correct")), "decisions": event.get("decisions"), "expected": event.get("expected"), "raw_source": str(EVENTS), "raw_line": line_by_id[lid], "raw_sha256": raw_sha, "reconstructed_sha256": hashlib.sha256(json.dumps({"logical_id": lid, "meta": meta, "correct": bool(event.get("correct")), "decisions": event.get("decisions"), "expected": event.get("expected")}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()})
    out = REPORT / "macro" / "checkpoint_reconstruction.csv"
    write_csv(out, rows)
    write_json(REPORT / "macro" / "checkpoint_reconstruction_audit.json", {"expected": len(expected), "journal_present": len(present), "missing": len(missing), "exactly_reconstructed": len(rows), "unexpected": len(unexpected), "ambiguous": 0, "imputed": 0, "rows": rows, "raw_sha256": raw_sha})
    if unexpected:
        raise AssertionError(f"unexpected checkpoint IDs: {unexpected[:3]}")
    return {"expected": len(expected), "present": len(present), "missing": len(missing), "rows": rows}


def _psi(matrix: np.ndarray) -> float:
    return float(psi_spec(matrix))


def reconstruct_competence(terminal: Mapping[str, Mapping[str, Any]]) -> tuple[list[dict[str, Any]], dict[tuple[str, int, str, int], dict[str, Any]]]:
    t0meta, cpmeta = expected_t0_ids(), expected_checkpoint_ids()
    observations: dict[tuple[str, int, str, int, int, int], list[dict[str, Any]]] = defaultdict(list)
    # t0 is deliberately shared by every cell; checkpoint observations are cell-specific.
    for lid, event in terminal.items():
        if lid in t0meta:
            m = t0meta[lid]
            for cell in MACRO_CELLS_V11:
                observations[(m["ecology"], m["seed"], str(cell["cell_id"]), 0, m["agent"], m["niche"])].append(event)
        elif lid in cpmeta:
            m = cpmeta[lid]
            observations[(m["ecology"], m["seed"], m["cell_id"], m["checkpoint"], m["agent"], m["niche"])].append(event)
        else:
            # online completion is not a probe observation
            continue
    rows: list[dict[str, Any]] = []
    matrices: dict[tuple[str, int, str, int], dict[str, Any]] = {}
    for ecology in ECOLOGIES:
        for seed in SOCIAL_SEEDS_V11[ecology]:
            for cell in MACRO_CELLS_V11:
                cid = str(cell["cell_id"])
                for checkpoint in CHECKPOINT_VALUES:
                    bit = np.zeros((N, K)); joint = np.zeros((N, K))
                    for agent in range(N):
                        for niche in range(K):
                            values = observations[(ecology, int(seed), cid, checkpoint, agent, niche)]
                            if len(values) != 8:
                                raise AssertionError(f"denominator mismatch {ecology}/{seed}/{cid}/{checkpoint}/{agent}/{niche}: {len(values)}")
                            bits = [_bits(value) for value in values]
                            bit[agent, niche] = float(np.mean(bits))
                            joint[agent, niche] = float(np.mean([bool(value.get("correct")) for value in values]))
                            for component in range(3):
                                rows.append({"ecology": ecology, "seed": int(seed), "cell_id": cid, "checkpoint": checkpoint, "agent": agent, "niche": niche, "metric": f"bit{component+1}", "accuracy": float(np.mean([x[component] for x in bits]))})
                            rows.append({"ecology": ecology, "seed": int(seed), "cell_id": cid, "checkpoint": checkpoint, "agent": agent, "niche": niche, "metric": "joint", "accuracy": float(joint[agent, niche])})
                    matrices[(ecology, int(seed), cid, checkpoint)] = {"bit": bit, "joint": joint, "psi_bit": _psi(bit), "psi_joint": _psi(joint)}
    write_csv(REPORT / "macro" / "competence_matrices.csv", rows)
    return rows, matrices


def _growth(values: Mapping[int, float]) -> float:
    x = np.asarray([16., 32., 64.]); y = np.asarray([math.log(float(values[t]) + 1e-6) for t in (16, 32, 64)])
    return float(np.polyfit(x, y, 1)[0])


def _rank_corr(a: list[float], b: list[float]) -> float | None:
    if len(set(a)) < 2 or len(set(b)) < 2:
        return None
    return float(spearmanr(a, b).statistic)


def compute_growth(matrices: Mapping[tuple[str, int, str, int], Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for ecology in ECOLOGIES:
        for seed in SOCIAL_SEEDS_V11[ecology]:
            for cell in MACRO_CELLS_V11:
                cid = str(cell["cell_id"])
                psi = {t: float(matrices[(ecology, int(seed), cid, t)]["psi_bit"]) for t in CHECKPOINT_VALUES}
                psi_joint = {t: float(matrices[(ecology, int(seed), cid, t)]["psi_joint"]) for t in CHECKPOINT_VALUES}
                row = {"ecology": ecology, "seed": int(seed), **cell, "g_obs": _growth(psi), "g_obs_joint": _growth(psi_joint)}
                for t in CHECKPOINT_VALUES:
                    row[f"psi_bit_{t}"] = psi[t]; row[f"psi_joint_{t}"] = psi_joint[t]
                rows.append(row)
    baseline = {(r["ecology"], r["seed"]): r["g_obs"] for r in rows if r["cell_id"] == "C0"}
    for row in rows:
        row["g_excess_obs"] = float(row["g_obs"] - baseline[(row["ecology"], row["seed"])])
        row["g_excess_obs_joint"] = float(row["g_obs_joint"] - next(x["g_obs_joint"] for x in rows if x["ecology"] == row["ecology"] and x["seed"] == row["seed"] and x["cell_id"] == "C0"))
    write_csv(REPORT / "macro" / "growth_by_seed.csv", rows)
    return rows


def scorecard(growth: list[dict[str, Any]]) -> dict[str, Any]:
    pred = json.loads((REPORT / "predictions" / "prediction_manifest.json").read_text(encoding="utf-8"))["prediction_rows"]
    pmap = {(r["ecology"], r["cell_id"]): r for r in pred}; omap = {(r["ecology"], r["cell_id"], r["seed"]): r for r in growth}
    keys = sorted(pmap)
    # V11-A: beta response, both ecology panels and pooled seed-mean cells.
    means = {(e, cid): float(np.mean([omap[(e, cid, s)]["g_excess_obs"] for s in SOCIAL_SEEDS_V11[e]])) for e, cid in keys}
    adaptive_ids = ["C0", "C1", "C2", "C3", "C4"]
    a_rows = [(e, cid) for e in ECOLOGIES for cid in adaptive_ids]
    a_pred = [pmap[k]["g_excess_pred"] for k in a_rows]; a_obs = [means[k] for k in a_rows]
    a_ecology = {e: _rank_corr([pmap[(e,c)]["g_excess_pred"] for c in adaptive_ids], [means[(e,c)] for c in adaptive_ids]) for e in ECOLOGIES}
    v11a = {"pooled_spearman": _rank_corr(a_pred, a_obs), "ecology_spearman": a_ecology, "status": "PASS" if _rank_corr(a_pred,a_obs) is not None and _rank_corr(a_pred,a_obs) >= .70 and all(v is not None and v >= .50 for v in a_ecology.values()) else "FAIL"}
    # V11-B, paired by ecology × seed.
    b = {}
    for e in ECOLOGIES:
        diffs = [omap[(e,"C2",s)]["g_excess_obs"] - omap[(e,"C5",s)]["g_excess_obs"] for s in SOCIAL_SEEDS_V11[e]]
        b[e] = {"seed_differences": diffs, "mean_difference": float(np.mean(diffs)), "status": "PASS" if abs(float(np.mean(diffs))) <= .002 else "FAIL"}
    v11b = {"ecology": b, "status": "PASS" if all(x["status"] == "PASS" for x in b.values()) else "FAIL"}
    # V11-C, q ordering and private-vs-full sharing at actual seed level.
    c = {}
    for e in ECOLOGIES:
        qmeans = {cid: float(np.mean([omap[(e,cid,s)]["g_excess_obs"] for s in SOCIAL_SEEDS_V11[e]])) for cid in ("C3","C6","C7")}
        private_gt_full = sum(omap[(e,"C3",s)]["g_excess_obs"] > omap[(e,"C7",s)]["g_excess_obs"] for s in SOCIAL_SEEDS_V11[e])
        c[e] = {"means": qmeans, "private_gt_shared_seeds": private_gt_full, "observed_order": qmeans["C3"] >= qmeans["C6"] >= qmeans["C7"]}
    v11c = {"ecology": c, "status": "PASS" if all(x["observed_order"] and x["private_gt_shared_seeds"] >= 5 for x in c.values()) else "FAIL"}
    # V11-D, adaptive amplification versus random private baseline.
    d = {}
    for e in ECOLOGIES:
        diffs = [omap[(e,"C3",s)]["g_excess_obs"] - omap[(e,"C0",s)]["g_excess_obs"] for s in SOCIAL_SEEDS_V11[e]]
        d[e] = {"seed_differences": diffs, "mean_difference": float(np.mean(diffs)), "positive_seeds": sum(x > 0 for x in diffs)}
    v11d = {"ecology": d, "status": "PASS" if all(x["mean_difference"] > 0 and x["positive_seeds"] >= 5 for x in d.values()) else "FAIL"}
    result = {"protocol": "THEORY-V1.1", "logical_calls": EXPECTED_LOGICAL, "tests": {"V11-A": v11a, "V11-B": v11b, "V11-C": v11c, "V11-D": v11d}, "prediction_sha256": hashlib.sha256((REPORT / "predictions" / "prediction_manifest.json").read_bytes()).hexdigest(), "scientific_unit": "environment/social seed", "notes": ["Psi and growth reconstructed from terminal raw completion events; checkpoint side-journal is auxiliary.", "No response-level p-values are used."]}
    passes = sum(result["tests"][name]["status"] == "PASS" for name in ("V11-B","V11-C","V11-D"))
    result["verdict"] = "CLEAN SUPPORT FOR CORE V1 MECHANISM" if v11a["status"] == "PASS" and passes >= 2 else ("MIXED" if v11a["status"] == "PASS" or passes > 0 else "CORE THEORY V1 MECHANISM NOT SUPPORTED UNDER CLEAN HARNESS")
    write_json(REPORT / "scorecard" / "v11_scorecard.json", result)
    flat = []
    for name, value in result["tests"].items():
        flat.append({"test": name, "status": value["status"], "details": json.dumps(value, sort_keys=True)})
    write_csv(REPORT / "scorecard" / "v11_scorecard.csv", flat)
    return result


def run_analysis() -> dict[str, Any]:
    terminal = terminal_events()
    cp_audit = reconstruct_checkpoint_aux(terminal)
    comp_rows, matrices = reconstruct_competence(terminal)
    growth = compute_growth(matrices)
    result = scorecard(growth)
    cp_ids = expected_checkpoint_ids(); t0_ids = expected_t0_ids()
    response_rows = []
    for lid, event in terminal.items():
        task = event.get("task") or {}
        if lid in t0_ids:
            phase, checkpoint, cell = "t0", 0, "COMMON_T0"
        elif lid in cp_ids:
            phase, checkpoint, cell = "checkpoint", cp_ids[lid]["checkpoint"], cp_ids[lid]["cell_id"]
        else:
            phase, checkpoint, cell = "online", None, event.get("cell_id")
        bits = _bits(event)
        response_rows.append({"logical_id": lid, "phase": phase, "ecology": event.get("ecology"), "seed": task.get("seed", event.get("seed")), "cell_id": cell, "checkpoint": checkpoint, "niche": task.get("niche"), "probe_index": task.get("probe_index"), "joint_correct": bool(event.get("correct")), "bit1_correct": bits[0], "bit2_correct": bits[1], "bit3_correct": bits[2], "error_category": event.get("error_category"), "attempt": event.get("attempt"), "model": (event.get("provider_metadata") or {}).get("model"), "fingerprint": (event.get("provider_metadata") or {}).get("system_fingerprint"), "latency_s": event.get("latency_s"), "cost_usd": event.get("attempt_cost_usd")})
    write_csv(REPORT / "macro" / "response_level.csv", response_rows)
    component_rows = []
    for ecology in ECOLOGIES:
        for cell in MACRO_CELLS_V11:
            cid = str(cell["cell_id"])
            for checkpoint in CHECKPOINT_VALUES:
                for component in range(3):
                    values = [r["accuracy"] for r in comp_rows if r["ecology"] == ecology and r["cell_id"] == cid and int(r["checkpoint"]) == checkpoint and r["metric"] == f"bit{component+1}"]
                    component_rows.append({"ecology": ecology, "cell_id": cid, "checkpoint": checkpoint, "component": component + 1, "mean_accuracy": float(np.mean(values)) if values else None})
    write_csv(REPORT / "macro" / "component_accuracy.csv", component_rows)
    write_json(REPORT / "scorecard" / "technical_health.json", {"logical_expected": EXPECTED_LOGICAL, "logical_terminal": len(terminal), "physical_attempts": len([r for r in load_jsonl(EVENTS) if r.get("event") == "completion"]), "retries": sum(int(r.get("attempt", 0)) for r in load_jsonl(EVENTS) if r.get("event") == "completion"), "checkpoint_reconstruction": cp_audit, "models": sorted({(r.get("provider_metadata") or {}).get("model") for r in terminal.values()}), "raw_events_sha256": hashlib.sha256(EVENTS.read_bytes()).hexdigest(), "prediction_sha256": result["prediction_sha256"]})
    return result


if __name__ == "__main__":
    print(json.dumps(run_analysis(), indent=2, sort_keys=True))
