"""Deterministic, offline forensic reconstruction for Theory V1.

This module deliberately reads the immutable MICRO/MACRO raw logs and writes
new artifacts under ``reports/theory-v1/repair``.  It never calls a provider,
never mutates raw logs, and never overwrites the historical sealed prediction
manifest.
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import os
import shutil
import subprocess
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from .dynamics import centered_projector, jacobian, retention, transfer_operator, psi_spec
from .micro_design import ECOLOGIES, K_VALUES, MICRO_SEEDS, MACRO_BETAS, MACRO_CHECKPOINTS, macro_cells
from .micro_estimation import estimate_k_explicit, estimate_k_pairwise, superposition_diagnostics
from .macro_runner import _lid
from .scoring import kendall_tau, pairwise_concordance, spearman

ROOT = Path(__file__).resolve().parents[3]
REPORT_ROOT = ROOT / "reports/theory-v1"
DATA_ROOT = ROOT / "data/auto-research/theory-v1"
MACRO_ROOT = DATA_ROOT / "macro"
REPAIR_ROOT = REPORT_ROOT / "repair"
MICRO_MANIFEST = REPORT_ROOT / "micro_execution_manifest.json"
MACRO_MANIFEST = REPORT_ROOT / "macro_execution_manifest.json"
MICRO_RAW = DATA_ROOT / "micro_events.jsonl"
MACRO_RAW = MACRO_ROOT / "macro_events.jsonl"
MACRO_CHECKPOINTS_RAW = MACRO_ROOT / "macro_checkpoint_observations.jsonl"
QUARANTINE_ID = "theory-v1-macro-aborted-serial-run-20260812"
CANONICAL_RUN_ID = "theory-v1-macro-confirmatory-restarted-20260812"
N = K = 4
TINY = 1e-12


def assert_scientific_run_allowed(run_id: str) -> None:
    """Hard firewall: the aborted serial run is never a scientific input."""
    if str(run_id) == QUARANTINE_ID:
        raise ValueError(f"quarantined Theory V1 run cannot enter scientific analysis: {run_id}")


def now() -> str:
    return datetime.now(UTC).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8")


def _json_default(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    raise TypeError(type(value).__name__)


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row}) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _terminal_by_id(events: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        # MICRO's historical raw schema omitted ``event: completion`` while
        # MACRO includes it; both use terminal logical observations.
        if event.get("event") == "completion" or ("terminal" in event and "task" in event):
            grouped[str(event["logical_id"])].append(dict(event))
    terminal: dict[str, dict[str, Any]] = {}
    for logical_id, rows in grouped.items():
        values = [row for row in rows if row.get("terminal")]
        if len(values) != 1:
            raise AssertionError(f"logical_id {logical_id} has {len(values)} terminal completions")
        terminal[logical_id] = values[0]
    return terminal


def _canonical_expected_ids(manifest: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Build the frozen logical-call identity map without inspecting answers."""
    expected: dict[str, dict[str, Any]] = {}
    for ecology in manifest["ecologies"]:
        for seed in manifest["social_seeds"][ecology]:
            seed = int(seed)
            for agent in range(N):
                for niche in range(K):
                    for probe in range(8):
                        lid = _lid("t0", ecology, seed, "COMMON_T0", 0, agent, niche, probe)
                        expected[lid] = {"phase": "t0", "ecology": ecology, "seed": seed, "cell_id": "COMMON_T0", "checkpoint": 0, "agent": agent, "niche": niche, "probe_index": probe}
            for cell in manifest["cells"]:
                cell_id = int(cell["cell_id"])
                for t in range(1, 129):
                    lid = _lid("online", ecology, seed, str(cell_id), t, -1, int(manifest["seed_specs"][f"{ecology}:{seed}"]["online"][t - 1]["niche"]), t=t)
                    expected[lid] = {"phase": "online", "ecology": ecology, "seed": seed, "cell_id": cell_id, "t": t}
                for checkpoint in MACRO_CHECKPOINTS[1:]:
                    for agent in range(N):
                        for niche in range(K):
                            for probe in range(8):
                                lid = _lid("checkpoint", ecology, seed, str(cell_id), checkpoint, agent, niche, probe)
                                expected[lid] = {"phase": "checkpoint", "ecology": ecology, "seed": seed, "cell_id": cell_id, "checkpoint": checkpoint, "agent": agent, "niche": niche, "probe_index": probe}
    return expected


def inventory() -> dict[str, Any]:
    """Create the no-conclusion forensic inventory requested by the protocol."""
    micro_manifest = load_json(MICRO_MANIFEST)
    macro_manifest = load_json(MACRO_MANIFEST)
    micro_events = load_jsonl(MICRO_RAW)
    macro_events = load_jsonl(MACRO_RAW)
    checkpoint_events = load_jsonl(MACRO_CHECKPOINTS_RAW)
    assert_scientific_run_allowed(CANONICAL_RUN_ID)
    macro_terminal = _terminal_by_id(macro_events)
    expected = _canonical_expected_ids(macro_manifest)
    checkpoint_expected = {lid for lid, row in expected.items() if row["phase"] == "checkpoint"}
    checkpoint_present = {str(row["logical_id"]) for row in checkpoint_events}
    missing = sorted(checkpoint_expected - checkpoint_present)
    unexpected = sorted(checkpoint_present - checkpoint_expected)
    if len(macro_terminal) != 186368:
        raise AssertionError(f"canonical MACRO terminal count is {len(macro_terminal)}, expected 186368")
    if unexpected:
        raise AssertionError(f"unexpected checkpoint IDs: {unexpected[:3]}")
    if any(lid not in expected for lid in macro_terminal):
        raise AssertionError("canonical MACRO contains an unknown logical ID")
    model_values = sorted({(event.get("provider_metadata") or {}).get("model") for event in macro_terminal.values() if (event.get("provider_metadata") or {}).get("model")})
    return {
        "created_at_utc": now(),
        "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "tags": subprocess.check_output(["git", "tag", "--list", "theory-v1*"], cwd=ROOT, text=True).split(),
        "micro_manifest_sha256": sha256_file(MICRO_MANIFEST),
        "macro_manifest_sha256": sha256_file(MACRO_MANIFEST),
        "prediction_seal_sha256": sha256_file(REPORT_ROOT / "prediction_seal.json"),
        "micro_raw_sha256_before": sha256_file(MICRO_RAW),
        "macro_raw_sha256_before": sha256_file(MACRO_RAW),
        "micro_raw_path": str(MICRO_RAW),
        "macro_raw_path": str(MACRO_RAW),
        "canonical_macro_run_id": CANONICAL_RUN_ID,
        "quarantined_aborted_run_id": QUARANTINE_ID,
        "micro_events": len(micro_events),
        "macro_physical_completion_events": sum(1 for row in macro_events if row.get("event") == "completion"),
        "macro_terminal_completions": len(macro_terminal),
        "macro_expected_logical_completions": int(macro_manifest["logical_calls"]),
        "checkpoint_expected": len(checkpoint_expected),
        "checkpoint_present": len(checkpoint_present),
        "checkpoint_missing_auxiliary": len(missing),
        "checkpoint_missing_ids": missing,
        "models": model_values,
        "quarantine_used_scientifically": False,
        "new_external_calls": 0,
    }


def reconstruct_checkpoint_records(inv: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    """Recover missing auxiliary rows from exact canonical raw completions."""
    manifest = load_json(MACRO_MANIFEST)
    raw_lines = MACRO_RAW.read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in raw_lines]
    terminal = _terminal_by_id(events)
    expected = _canonical_expected_ids(manifest)
    present = {str(row["logical_id"]) for row in load_jsonl(MACRO_CHECKPOINTS_RAW)}
    rows: list[dict[str, Any]] = []
    for line_no, event in enumerate(events, 1):
        lid = str(event.get("logical_id"))
        meta = expected.get(lid)
        if not meta or meta["phase"] != "checkpoint" or lid in present or not event.get("terminal"):
            continue
        task = event.get("task") or {}
        if int(task.get("checkpoint", -1)) != int(meta["checkpoint"]):
            raise AssertionError(f"checkpoint mismatch for {lid}")
        row = {
            "protocol": "THEORY-V1", "event": "checkpoint_observation", "logical_id": lid,
            "ecology": meta["ecology"], "seed": meta["seed"], "cell_id": meta["cell_id"],
            "checkpoint": meta["checkpoint"], "agent": meta["agent"], "niche": meta["niche"],
            "probe_index": meta["probe_index"], "correct": bool(event.get("correct")),
            "memory_hash": hashlib.sha256(json.dumps(event.get("memory", []), sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "memory_hash_after": "RECONSTRUCTED_FROM_RAW_EVENT",
            "no_mutation": True,
            "raw_source_path": str(MACRO_RAW), "raw_line": line_no,
            "raw_file_sha256": sha256_file(MACRO_RAW),
            "reconstructed_record_sha256": hashlib.sha256(json.dumps({"logical_id": lid, "correct": bool(event.get("correct")), "meta": meta}, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        }
        # Exact answer/truth identity is included in the audit payload, not in
        # the legacy journal schema.
        row["decisions"] = event.get("decisions")
        row["expected"] = event.get("expected")
        rows.append(row)
    if inv is not None and len(rows) != int(inv["checkpoint_missing_auxiliary"]):
        raise AssertionError("reconstructed checkpoint count differs from inventory")
    if len(rows) != 31:
        raise AssertionError(f"expected exactly 31 reconstructed checkpoint rows, got {len(rows)}")
    write_csv(REPAIR_ROOT / "reconstructed_checkpoint_records.csv", rows)
    write_json(REPAIR_ROOT / "checkpoint_reconstruction_audit.json", {
        "missing_auxiliary_records": len(rows), "exactly_reconstructed": len(rows),
        "ambiguous": 0, "imputed": 0, "raw_source": str(MACRO_RAW), "raw_sha256": sha256_file(MACRO_RAW),
        "rows": rows,
    })
    return rows


def _micro_terminal_rows() -> list[dict[str, Any]]:
    events = load_jsonl(MICRO_RAW)
    terminal = _terminal_by_id(events)
    rows: list[dict[str, Any]] = []
    # The historical MICRO manifest is a frozen task set, but concurrent
    # execution persisted attempts in a different physical order.  The raw
    # completion's embedded task is therefore the canonical join key here;
    # this avoids positional joins while still requiring the manifest count.
    for event in terminal.values():
        task = event.get("task")
        if not isinstance(task, dict):
            raise AssertionError("MICRO terminal lacks embedded task")
        decisions = event.get("decisions")
        rows.append({**task, "decisions": decisions, "expected": task["probe"]["y"], "correct": bool(decisions is not None and decisions == task["probe"]["y"])})
    if len(rows) != int(load_json(MICRO_MANIFEST)["logical_calls"]):
        raise AssertionError(f"MICRO terminal count {len(rows)} does not match manifest")
    return rows


def _micro_unit_estimates() -> tuple[dict[tuple[str, int, int], np.ndarray], dict[tuple[str, int, int], np.ndarray], dict[tuple[str, int, int], dict[str, float]], dict[tuple[str, int, int], list[np.ndarray]]]:
    rows = _micro_terminal_rows()
    grouped: dict[tuple[str, int, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["ecology"], int(row["seed"]), int(row["k"]), int(row["state_index"]))].append(row)
    explicit: dict[tuple[str, int, int], np.ndarray] = {}
    pairwise: dict[tuple[str, int, int], np.ndarray] = {}
    diagnostics: dict[tuple[str, int, int], dict[str, float]] = {}
    response_vectors: dict[tuple[str, int, int], list[np.ndarray]] = {}
    from .micro_design import double_swaps, single_swaps
    for ecology in ECOLOGIES:
        for seed in MICRO_SEEDS[ecology]:
            for k in K_VALUES:
                base = np.asarray([np.mean([r["correct"] for r in grouped[(ecology, seed, k, 0)] if int(r["target"]) == target]) for target in range(K)], dtype=float)
                singles = single_swaps(seed, k)
                vectors = []
                swaps = []
                for index, swap in enumerate(singles):
                    values = np.asarray([np.mean([r["correct"] for r in grouped[(ecology, seed, k, index + 1)] if int(r["target"]) == target]) for target in range(K)], dtype=float)
                    vectors.append(values - base)
                    delta = np.zeros(K); delta[int(swap["target"])] += 1; delta[int(swap["source"])] -= 1
                    swaps.append(delta)
                key = (ecology, int(seed), int(k))
                e = estimate_k_explicit(swaps, vectors); p = estimate_k_pairwise(swaps, vectors)
                explicit[key] = e; pairwise[key] = p; response_vectors[key] = vectors
                observed = []; predicted = []
                for index, pair in enumerate(double_swaps(seed, k)):
                    state_index = 13 + index
                    actual = np.asarray([np.mean([r["correct"] for r in grouped[(ecology, seed, k, state_index)] if int(r["target"]) == target]) for target in range(K)], dtype=float) - base
                    left = singles.index(pair[0]); right = singles.index(pair[1])
                    observed.append(actual); predicted.append(vectors[left] + vectors[right])
                diag = superposition_diagnostics(observed, predicted)
                diag["mean_absolute_error"] = float(np.mean(np.abs(np.asarray(observed) - np.asarray(predicted))))
                diag["maximum_absolute_error"] = float(np.max(np.abs(np.asarray(observed) - np.asarray(predicted))))
                diagnostics[key] = diag
    return explicit, pairwise, diagnostics, response_vectors


def reconstruct_k() -> dict[str, Any]:
    explicit, pairwise, diagnostics, responses_by_unit = _micro_unit_estimates()
    pooled: dict[str, dict[str, np.ndarray]] = {e: {} for e in ECOLOGIES}
    seed_mean: dict[str, dict[str, np.ndarray]] = {e: {} for e in ECOLOGIES}
    estimators: list[dict[str, Any]] = []
    from .micro_design import single_swaps
    for ecology in ECOLOGIES:
        for k in K_VALUES:
            all_swaps: list[np.ndarray] = []; all_resp: list[np.ndarray] = []
            for seed in MICRO_SEEDS[ecology]:
                key = (ecology, int(seed), int(k)); all_swaps.extend([np.eye(K)[int(s["target"])] - np.eye(K)[int(s["source"])] for s in single_swaps(seed, k)]); all_resp.extend(responses_by_unit[key])
            pooled_e = estimate_k_explicit(all_swaps, all_resp); pooled_p = estimate_k_pairwise(all_swaps, all_resp)
            mean_e = np.mean([explicit[(ecology, int(seed), int(k))] for seed in MICRO_SEEDS[ecology]], axis=0)
            mean_p = np.mean([pairwise[(ecology, int(seed), int(k))] for seed in MICRO_SEEDS[ecology]], axis=0)
            pooled[ecology][str(k)] = pooled_e; seed_mean[ecology][str(k)] = mean_e
            estimators.append({"ecology": ecology, "k": k, "pooled_explicit_pairwise_max_abs_diff": float(np.max(np.abs(pooled_e - pooled_p))), "seed_mean_explicit_pairwise_max_abs_diff": float(np.max(np.abs(mean_e - mean_p))), "pooled_vs_seed_mean_max_abs_diff": float(np.max(np.abs(pooled_e - mean_e)))})
    rows = []
    for key, matrix in explicit.items():
        ecology, seed, k = key
        rows.append({"ecology": ecology, "seed": seed, "k": k, "K": matrix.tolist(), "pairwise_K": pairwise[key].tolist(), "max_estimator_diff": float(np.max(np.abs(matrix - pairwise[key]))), **diagnostics[key]})
    write_json(REPAIR_ROOT / "k_reconstruction.json", {"primary": "pooled_all_8_micro_seeds", "pooled": pooled, "seed_mean": seed_mean, "seed_level": rows, "estimator_comparison": estimators})
    write_csv(REPAIR_ROOT / "micro_linearity_diagnostics.csv", [{"ecology": e, "seed": s, "k": k, **diagnostics[(e, s, k)]} for e, s, k in diagnostics])
    return {"primary": pooled, "seed_mean": seed_mean, "seed_level": rows, "estimators": estimators}


def centered_basis(size: int = K) -> np.ndarray:
    p = centered_projector(size)
    u, _, _ = np.linalg.svd(p)
    return u[:, : size - 1]


def centered_spectrum(matrix: Sequence[Sequence[float]], k: int, beta: float, epsilon: float, q_share: float) -> dict[str, Any]:
    full = jacobian(matrix, k, q_share, beta, epsilon)
    basis = centered_basis(len(matrix))
    restricted = basis.T @ full @ basis
    values, vectors = np.linalg.eig(restricted)
    magnitudes = np.abs(values)
    order = np.argsort(magnitudes)[::-1]
    radius = float(magnitudes[order[0]]) if len(order) else 0.0
    second = float(magnitudes[order[1]]) if len(order) > 1 else 0.0
    mode = basis @ np.real(vectors[:, order[0]]) if len(order) else np.zeros(len(matrix))
    mode = mode / (np.linalg.norm(mode) or 1.0)
    t = transfer_operator(matrix)
    t_centered = basis.T @ t @ basis
    chi = float(np.max(np.real(np.linalg.eigvals(t_centered))))
    beta_critical = None if q_share == 1.0 or epsilon == 1.0 or chi <= TINY else float(N * (1.0 - retention(k, q_share, N)) / ((1.0 - q_share) * (1.0 - epsilon) * chi))
    return {"J_full": full.tolist(), "J_centered": restricted.tolist(), "centered_eigenvalues_real": [float(v.real) for v in values], "centered_eigenvalues_imag": [float(v.imag) for v in values], "R_spec": radius, "lambda_spec": math.log(radius) if radius > 0 else float("-inf"), "g_pred": 2 * math.log(radius) if radius > 0 else float("-inf"), "dominant_mode": mode.tolist(), "relative_spectral_gap": (radius - second) / radius if radius > TINY else 0.0, "full_spectral_radius": float(np.max(np.abs(np.linalg.eigvals(full)))), "beta_critical": beta_critical}


def _regime(radius: float) -> str:
    if radius <= .98: return "SUBCRITICAL"
    if radius < 1.02: return "TRANSITIONAL"
    return "SUPERCRITICAL"


def repaired_predictions(k_data: Mapping[str, Mapping[str, np.ndarray]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ecology in ECOLOGIES:
        for k in K_VALUES:
            matrix = np.asarray(k_data[ecology][str(k)], dtype=float)
            base_spec = centered_spectrum(matrix, k, 0.0, .10, 0.0)
            for cell in macro_cells():
                spec = centered_spectrum(matrix, int(cell["k"]), float(cell["beta"]), float(cell["epsilon"]), float(cell["q_share"])) if int(cell["k"]) == k else centered_spectrum(matrix, int(cell["k"]), float(cell["beta"]), float(cell["epsilon"]), float(cell["q_share"]))
                # The hard invariant is that the prediction matrix is selected
                # by the social cell's k, never by a neighboring K.
                if int(cell["k"]) != k:
                    continue
                row = {"ecology": ecology, **cell, "K_identifier": f"{ecology}:pooled:{k}", "K_hash": hashlib.sha256(json.dumps(matrix.tolist(), separators=(",", ":")).encode()).hexdigest(), "T_hash": hashlib.sha256(json.dumps(transfer_operator(matrix).tolist(), separators=(",", ":")).encode()).hexdigest(), "J_hash": hashlib.sha256(json.dumps(spec["J_full"], separators=(",", ":")).encode()).hexdigest(), **{key: value for key, value in spec.items() if key not in {"J_full", "J_centered"}}, "regime": _regime(spec["R_spec"])}
                row["g_excess_pred"] = float(row["g_pred"] - base_spec["g_pred"])
                rows.append(row)
    if len(rows) != 36:
        raise AssertionError(f"repaired population prediction cardinality {len(rows)} != 36")
    keys = [(r["ecology"], int(r["k"]), float(r["beta"]), float(r["epsilon"]), float(r["q_share"])) for r in rows]
    if len(keys) != len(set(keys)) or any(f":{int(r['k'])}" not in str(r["K_identifier"]) for r in rows):
        raise AssertionError("duplicate prediction key or k/K mismatch")
    write_json(REPAIR_ROOT / "prediction_manifest_forensic_repair.json", {"protocol": "THEORY-V1", "status": "FORENSIC_REPAIR_AFTER_MACRO", "mathematical_specification": "frozen prospectively", "original_implementation": "buggy", "forensic_reconstruction": "generated after MACRO data existed", "equations_changed": False, "implementation_changed": True, "aggregation": "pooled all eight MICRO seeds per ecology×k", "prediction_rows": rows})
    write_csv(REPAIR_ROOT / "prediction_table_repaired.csv", rows)
    return rows


def _correct_bits(event: Mapping[str, Any]) -> list[bool]:
    decisions, expected = event.get("decisions"), event.get("expected")
    if not isinstance(decisions, list) or not isinstance(expected, list) or len(decisions) != len(expected):
        return [False, False, False]
    return [a == b for a, b in zip(decisions, expected)]


def observed_checkpoint_data() -> dict[str, Any]:
    manifest = load_json(MACRO_MANIFEST)
    events = load_jsonl(MACRO_RAW)
    step_events = [row for row in events if row.get("event") == "online_step"]
    terminal = _terminal_by_id(events)
    expected = _canonical_expected_ids(manifest)
    obs: dict[tuple[str, int, int, int, int, int], list[dict[str, Any]]] = defaultdict(list)
    # Key: ecology, seed, cell, checkpoint, agent, niche.  The t0 rows are
    # intentionally reused for every social cell, as required by the protocol.
    for lid, event in terminal.items():
        meta = expected.get(lid)
        if not meta or meta["phase"] not in {"t0", "checkpoint"}: continue
        cell_ids = [int(c["cell_id"]) for c in manifest["cells"]] if meta["phase"] == "t0" else [int(meta["cell_id"])]
        for cell in cell_ids:
            obs[(meta["ecology"], int(meta["seed"]), cell, int(meta["checkpoint"]), int(meta["agent"]), int(meta["niche"]))].append(event)
    matrices: dict[str, dict[str, dict[str, Any]]] = {}
    per_seed: list[dict[str, Any]] = []
    for ecology in ECOLOGIES:
        for seed in manifest["social_seeds"][ecology]:
            for cell in manifest["cells"]:
                cell_id = int(cell["cell_id"])
                checkpoint_values = {}
                for checkpoint in MACRO_CHECKPOINTS:
                    bit = np.zeros((N, K)); joint = np.zeros((N, K))
                    for agent in range(N):
                        for niche in range(K):
                            values = obs[(ecology, int(seed), cell_id, int(checkpoint), agent, niche)]
                            if len(values) != 8: raise AssertionError(f"observation denominator mismatch {ecology}/{seed}/{cell_id}/{checkpoint}/{agent}/{niche}: {len(values)}")
                            bit_values = [_correct_bits(value) for value in values]
                            bit[agent, niche] = float(np.mean(bit_values))
                            joint[agent, niche] = float(np.mean([bool(value.get("correct")) for value in values]))
                    for name, matrix in (("bit", bit), ("joint", joint)):
                        if np.any(matrix < -TINY) or np.any(matrix > 1 + TINY): raise AssertionError("competence outside [0,1]")
                    secondary = _secondary_metrics(bit, joint, [row for row in step_events if row.get("ecology") == ecology and int(row.get("seed")) == int(seed) and int(row.get("cell_id")) == cell_id and int(row.get("t", 0)) <= int(checkpoint)])
                    checkpoint_values[str(checkpoint)] = {"bit": bit.tolist(), "joint": joint.tolist(), "psi_bit": psi_spec(bit), "psi_joint": psi_spec(joint), **secondary}
                base = checkpoint_values["0"]
                g_bit = _growth(checkpoint_values, "psi_bit")
                g_joint = _growth(checkpoint_values, "psi_joint")
                per_seed.append({"ecology": ecology, "seed": int(seed), "cell_id": cell_id, "k": int(cell["k"]), "beta": float(cell["beta"]), "epsilon": float(cell["epsilon"]), "q_share": float(cell["q_share"]), "g_obs_bit": g_bit, "g_obs_joint": g_joint, "psi_bit_0": base["psi_bit"], "psi_joint_0": base["psi_joint"], "psi_bit_16": checkpoint_values["16"]["psi_bit"], "psi_bit_32": checkpoint_values["32"]["psi_bit"], "psi_bit_64": checkpoint_values["64"]["psi_bit"], "psi_bit_128": checkpoint_values["128"]["psi_bit"], "psi_joint_128": checkpoint_values["128"]["psi_joint"], "checkpoint_values": checkpoint_values})
    write_csv(REPAIR_ROOT / "observed_seed_cell_metrics.csv", [{k: v for k, v in row.items() if k != "checkpoint_values"} for row in per_seed])
    secondary_rows = []
    for row in per_seed:
        for checkpoint, values in row["checkpoint_values"].items():
            secondary_rows.append({"ecology": row["ecology"], "seed": row["seed"], "cell_id": row["cell_id"], "checkpoint": int(checkpoint), **{key: values.get(key) for key in ("psi_bit", "psi_joint", "u_match", "u_single", "delta_match", "oracle_accuracy", "team_accuracy", "routing_entropy", "task_agent_mi", "eta_route")}})
    write_csv(REPAIR_ROOT / "formation_exploitation_secondary.csv", secondary_rows)
    write_json(REPAIR_ROOT / "competence_reconstruction.json", {"source": str(MACRO_RAW), "method": "raw terminal completion events", "denominator_per_agent_niche_checkpoint": 8, "rows": per_seed})
    return {"rows": per_seed, "observation_count": len(obs)}


def _secondary_metrics(bit: np.ndarray, joint: np.ndarray, steps: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Secondary formation/exploitation diagnostics; never used by T1–T9."""
    permutations = list(itertools.permutations(range(N)))
    u_match = max(float(np.mean([bit[perm[c], c] for c in range(K)])) for perm in permutations)
    u_single = float(np.max(np.mean(bit, axis=1)))
    oracle = float(np.mean(np.max(bit, axis=0)))
    team = float(np.mean(np.max(joint, axis=0)))
    routing_entropy = None; task_agent_mi = None; eta_route = None
    if steps:
        counts = Counter((int(step["task"]["niche"]), int(step["selected_agent"])) for step in steps)
        niche_counts = Counter(int(step["task"]["niche"]) for step in steps); agent_counts = Counter(int(step["selected_agent"]) for step in steps); total = len(steps)
        probs = [count / total for count in agent_counts.values()]
        routing_entropy = float(-sum(p * math.log(p) for p in probs if p > 0) / math.log(N)) if N > 1 else 0.0
        mi = 0.0
        for (niche, agent), count in counts.items():
            p_joint = count / total; p_n = niche_counts[niche] / total; p_a = agent_counts[agent] / total
            mi += p_joint * math.log(p_joint / (p_n * p_a))
        task_agent_mi = float(mi)
        route_utility = sum((niche_counts[niche] / total) * sum(counts[(niche, agent)] / niche_counts[niche] * bit[agent, niche] for agent in range(N)) for niche in range(K))
        random_utility = float(np.mean(bit))
        eta_route = float((route_utility - random_utility) / (oracle - random_utility)) if oracle > random_utility + TINY else None
    return {"u_match": u_match, "u_single": u_single, "delta_match": u_match - u_single, "oracle_accuracy": oracle, "team_accuracy": team, "routing_entropy": routing_entropy, "task_agent_mi": task_agent_mi, "eta_route": eta_route}


def _growth(values: Mapping[str, Mapping[str, Any]], metric: str) -> float:
    xs = np.asarray([16.0, 32.0, 64.0]); ys = np.asarray([math.log(float(values[str(t)][metric]) + 1e-6) for t in (16, 32, 64)])
    return float(np.polyfit(xs, ys, 1)[0])


def _aggregate_observed(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        key = tuple(row[key] for key in ("ecology", "cell_id", "k", "beta", "epsilon", "q_share")); by_key[key].append(row)
    out = []
    for key, values in sorted(by_key.items(), key=lambda item: item[0]):
        ecology, cell_id, k, beta, epsilon, q = key
        out.append({"ecology": ecology, "cell_id": int(cell_id), "k": int(k), "beta": float(beta), "epsilon": float(epsilon), "q_share": float(q), "g_excess_obs": float(np.mean([v["g_obs_bit"] for v in values])), "g_excess_obs_joint": float(np.mean([v["g_obs_joint"] for v in values])), "seed_values": [v["g_obs_bit"] for v in values], "seed_count": len(values), "psi_bit_128": float(np.mean([v["psi_bit_128"] for v in values])), "psi_joint_128": float(np.mean([v["psi_joint_128"] for v in values]))})
    baseline = {(r["ecology"], r["k"]): r["g_excess_obs"] for r in out if r["beta"] == 0 and r["q_share"] == 0 and r["epsilon"] == .1}
    for row in out: row["g_excess_obs"] = float(row["g_excess_obs"] - baseline[(row["ecology"], row["k"])])
    return out


def scorecard(predictions: Sequence[Mapping[str, Any]], observed_rows: Sequence[Mapping[str, Any]], *, write_artifacts: bool = True) -> dict[str, Any]:
    observed = _aggregate_observed(observed_rows)
    key = lambda r: (r["ecology"], int(r["k"]), float(r["beta"]), float(r["epsilon"]), float(r["q_share"]))
    pmap = {key(r): r for r in predictions}; omap = {key(r): r for r in observed}
    if set(pmap) != set(omap): raise AssertionError("prediction/observation keys do not align")
    order = sorted(pmap)
    pred = [float(pmap[k]["g_excess_pred"]) for k in order]; obs = [float(omap[k]["g_excess_obs"]) for k in order]
    ecology_slices = {e: [i for i, k0 in enumerate(order) if k0[0] == e] for e in ECOLOGIES}
    t1 = {"test": "T1", "pooled_spearman": spearman(pred, obs), "ecology_spearman": {e: spearman([pred[i] for i in idx], [obs[i] for i in idx]) for e, idx in ecology_slices.items()}, "pooled_kendall": kendall_tau(pred, obs), "ecology_kendall": {e: kendall_tau([pred[i] for i in idx], [obs[i] for i in idx]) for e, idx in ecology_slices.items()}, "pairwise": pairwise_concordance(pred, obs, .002)}
    t1["status"] = "PASS" if t1["pooled_spearman"] >= .7 and all(v >= .5 for v in t1["ecology_spearman"].values()) else "FAIL"
    # T2 is within-ecology only and uses the frozen .002 margin.
    t2_panels = {}
    for e in ECOLOGIES:
        idx = ecology_slices[e]; t2_panels[e] = pairwise_concordance([pred[i] for i in idx], [obs[i] for i in idx], .002)
    t2 = {"test": "T2", "panels": t2_panels, "eligible": sum(v["eligible"] for v in t2_panels.values()), "correct": sum(v["correct"] for v in t2_panels.values()), "status": "NON_IDENTIFIABLE" if sum(v["eligible"] for v in t2_panels.values()) < 10 else ("PASS" if sum(v["correct"] for v in t2_panels.values()) / sum(v["eligible"] for v in t2_panels.values()) >= .75 else "FAIL")}
    panels = []
    for e in ECOLOGIES:
        for k0 in K_VALUES:
            # Frozen T3 is exactly the private epsilon=.10 beta grid.  The
            # matched-gain beta=16, epsilon=.55 cell is not a T3 panel.
            keys = [x for x in order if x[0] == e and x[1] == k0 and x[2] in MACRO_BETAS and x[3] == .1 and x[4] == 0]
            p = [pmap[x]["g_excess_pred"] for x in sorted(keys, key=lambda x: x[2])]; o = [omap[x]["g_excess_obs"] for x in sorted(keys, key=lambda x: x[2])]
            rho = spearman(p, o)
            panels.append({"ecology": e, "k": k0, "n_beta_cells": len(keys), "betas": list(MACRO_BETAS), "spearman": rho, "predicted": p, "observed": o})
    if any(panel["n_beta_cells"] != len(MACRO_BETAS) for panel in panels):
        raise AssertionError("T3 requires exactly five private beta cells per ecology x k panel")
    t3 = {"test": "T3", "panels": panels, "panels_passing": sum(np.isfinite(x["spearman"]) and x["spearman"] >= .7 for x in panels), "status": "PASS" if sum(np.isfinite(x["spearman"]) and x["spearman"] >= .7 for x in panels) >= 5 else "FAIL"}
    t4 = {"test": "T4", "ecology": {}}
    for e in ECOLOGIES:
        left_rows = [r for r in observed_rows if r["ecology"] == e and r["k"] == 8 and r["beta"] == 8 and r["epsilon"] == .1 and r["q_share"] == 0]
        right_rows = [r for r in observed_rows if r["ecology"] == e and r["k"] == 8 and r["beta"] == 16 and r["epsilon"] == .55 and r["q_share"] == 0]
        left = {int(r["seed"]): r["g_obs_bit"] for r in left_rows}
        right = {int(r["seed"]): r["g_obs_bit"] for r in right_rows}
        if len(left_rows) != 8 or len(right_rows) != 8 or len(left) != 8 or len(right) != 8:
            raise AssertionError("T4 requires exactly one observation per ecology x seed x matched cell")
        # Pair by ecology and social seed, never by cell_id.  Subtracting the
        # same beta=0 baseline cancels in the paired difference, but this keeps
        # the reported values on the frozen excess-growth scale.
        diffs = [float(left[x] - right[x]) for x in sorted(set(left) & set(right))]
        t4["ecology"][e] = {"seed_differences": diffs, "mean_difference": float(np.mean(diffs)) if diffs else None, "status": "PASS" if diffs and abs(float(np.mean(diffs))) <= .002 else "FAIL"}
    t4["status"] = "PASS" if all(v["status"] == "PASS" for v in t4["ecology"].values()) else "FAIL"
    t5 = {"test": "T5", "ecology": {}}
    for e in ECOLOGIES:
        baseline_rows = [r for r in observed_rows if r["ecology"] == e and r["k"] == 8 and r["beta"] == 0 and r["epsilon"] == .1 and r["q_share"] == 0]
        baseline = {int(r["seed"]): float(r["g_obs_bit"]) for r in baseline_rows}
        vals = {}
        for q in (0.0, .5, 1.0):
            q_rows = [r for r in observed_rows if r["ecology"] == e and r["k"] == 8 and r["beta"] == 12 and r["epsilon"] == .1 and r["q_share"] == q]
            q_map = {int(r["seed"]): float(r["g_obs_bit"]) - baseline[int(r["seed"])] for r in q_rows}
            if len(q_rows) != 8 or len(q_map) != 8:
                raise AssertionError("T5 requires exactly eight seed-level observations for each q condition")
            vals[q] = q_map
        if len(baseline_rows) != 8 or len(baseline) != 8:
            raise AssertionError("T5 requires eight seed-level observations for each q condition")
        means = {str(q): float(np.mean(list(v.values()))) if v else None for q, v in vals.items()}
        seed_positive = sum(vals[0.0][seed] > vals[1.0][seed] for seed in sorted(set(vals[0.0]) & set(vals[1.0])))
        t5["ecology"][e] = {"means": means, "seed_values": {str(q): [vals[q][seed] for seed in sorted(vals[q])] for q in vals}, "private_positive_seeds": seed_positive, "seed_count": len(vals[0.0]), "predicted_order": "0>.5>1", "observed_order": means.get("0.0") is not None and means["0.0"] >= means["0.5"] >= means["1.0"]}
    t5["status"] = "PASS" if all(v["observed_order"] and v["private_positive_seeds"] >= 6 for v in t5["ecology"].values()) else "FAIL"
    # T6 consumes the complete eligible private k x beta grid: all frozen
    # capacities and all five private beta values, both ecologies.
    t6_pred = []; t6_obs = []
    for e in ECOLOGIES:
        for k0 in K_VALUES:
            for beta0 in MACRO_BETAS:
                x = (e, k0, beta0, .1, 0.0)
                if x not in pmap or x not in omap:
                    raise AssertionError(f"T6 missing eligible private cell {x}")
                t6_pred.append(pmap[x]["g_excess_pred"]); t6_obs.append(omap[x]["g_excess_obs"])
    t6_rho = spearman(t6_pred, t6_obs)
    t6 = {"test": "T6", "eligible_cells": len(t6_pred), "predicted": t6_pred, "observed": t6_obs, "spearman": t6_rho, "status": "PASS" if t6_rho >= .7 else "FAIL"}
    # T7 uses all 36 repaired population rows. Transitional rows are excluded.
    t7_pairs = [(r["regime"], bool(omap[key(r)]["g_excess_obs"] > 0), key(r)) for r in predictions if key(r) in omap]
    eligible = [(p, o, k0) for p, o, k0 in t7_pairs if p != "TRANSITIONAL"]
    t7 = {"test": "T7", "subcritical": sum(p == "SUBCRITICAL" for p, _, _ in t7_pairs), "transitional": sum(p == "TRANSITIONAL" for p, _, _ in t7_pairs), "supercritical": sum(p == "SUPERCRITICAL" for p, _, _ in t7_pairs), "eligible": len(eligible), "accuracy": (sum((p == "SUPERCRITICAL") == o for p, o, _ in eligible) / len(eligible) if eligible else None)}
    t7["status"] = "NON_IDENTIFIABLE" if len(eligible) < 8 else ("PASS" if t7["accuracy"] >= .75 else "FAIL")
    t8 = {"test": "T8", "ecology_t1": t1["ecology_spearman"], "major_laws": {"sharing": t5["status"] == "PASS", "matched_gain": t4["status"] == "PASS"}, "status": "PASS" if all(v >= .5 for v in t1["ecology_spearman"].values()) and t5["status"] == "PASS" and t4["status"] == "PASS" else "FAIL"}
    energies = []
    for row in predictions:
        if row["R_spec"] > 1.02 and row["relative_spectral_gap"] >= .20:
            mat = np.asarray(next(x for x in observed_rows if key(x) == key(row))["checkpoint_values"]["128"]["bit"])
            z = centered_projector(N) @ mat @ centered_projector(K); v = np.asarray(row["dominant_mode"]); energies.append(float(np.linalg.norm(z @ v) ** 2 / (np.linalg.norm(z) ** 2 or 1.0)))
    t9 = {"test": "T9", "eligible": len(energies), "mean_mode_energy": float(np.mean(energies)) if energies else None, "fraction_above_isotropic": float(np.mean(np.asarray(energies) > 1/3)) if energies else None, "status": "NON_IDENTIFIABLE" if not energies else ("PASS" if np.mean(energies) >= .5 and np.mean(np.asarray(energies) > 1/3) >= .75 else "FAIL")}
    result = {"protocol": "THEORY-V1", "status": "FORENSIC_REPAIRED_SCORECARD", "tests": {"T1": t1, "T2": t2, "T3": t3, "T4": t4, "T5": t5, "T6": t6, "T7": t7, "T8": t8, "T9": t9}, "observed_cell_rows": observed, "prediction_rows": list(predictions)}
    passed = [result["tests"][f"T{i}"]["status"] == "PASS" for i in range(1, 10)]
    if all(passed[i - 1] for i in (1, 5, 8)) and sum(passed[i - 1] for i in (2, 3, 4, 6, 7)) >= 3: overall = "STRONGLY SUPPORTED"
    elif result["tests"]["T1"]["status"] == "PASS": overall = "PARTIALLY SUPPORTED"
    elif result["tests"]["T1"]["status"] == "FAIL": overall = "NOT SUPPORTED IN CURRENT FORM"
    else: overall = "GLOBAL LABEL AMBIGUOUS UNDER FROZEN RULES"
    result["global_verdict"] = overall
    if write_artifacts:
        write_json(REPAIR_ROOT / "theory_v1_scorecard_repaired.json", result)
        flat = []
        for name, value in result["tests"].items():
            flat.append({"test": name, "status": value.get("status"), "statistic": value.get("pooled_spearman", value.get("accuracy", value.get("mean_difference"))), "units": value.get("eligible", value.get("panels_passing"))})
        write_csv(REPAIR_ROOT / "theory_v1_scorecard_repaired.csv", flat)
    return result


def sensitivity_scorecards(k_data: Mapping[str, Any], observed_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Evaluate only aggregation interpretations compatible with the frozen text."""
    interpretations: dict[str, list[dict[str, Any]]] = {}
    interpretations["seed_mean_K"] = repaired_predictions(k_data["seed_mean"])
    by_key: dict[tuple[str, int, float, float, float], list[dict[str, Any]]] = defaultdict(list)
    for seed_index in range(8):
        matrices = {ecology: {str(k): np.asarray(k_data["seed_level_map"][(ecology, int(MICRO_SEEDS[ecology][seed_index]), int(k))]) for k in K_VALUES} for ecology in ECOLOGIES}
        for row in repaired_predictions(matrices):
            key = (row["ecology"], int(row["k"]), float(row["beta"]), float(row["epsilon"]), float(row["q_share"]))
            by_key[key].append(row)
    averaged: list[dict[str, Any]] = []
    for key, values in sorted(by_key.items()):
        first = dict(values[0])
        for field in ("R_spec", "lambda_spec", "g_pred", "g_excess_pred"):
            first[field] = float(np.mean([float(value[field]) for value in values]))
        first["aggregation"] = "prediction_per_micro_seed_then_mean"
        averaged.append(first)
    interpretations["prediction_per_micro_seed_then_mean"] = averaged
    outputs = {}
    for name, predictions in interpretations.items():
        result = scorecard(predictions, observed_rows, write_artifacts=False)
        outputs[name] = {"global_verdict": result["global_verdict"], "tests": result["tests"]}
    write_json(REPAIR_ROOT / "sensitivity_scorecards.json", {"primary_interpretation": "pooled_K", "interpretations": outputs, "selection_rule": "literal frozen specification; no post-MACRO performance selection"})
    return outputs


def run_forensic_repair() -> dict[str, Any]:
    before = inventory(); write_json(REPAIR_ROOT / "forensic_inventory.json", before)
    reconstruct_checkpoint_records(before)
    k_data = reconstruct_k()
    predictions = repaired_predictions(k_data["primary"])
    observed = observed_checkpoint_data()
    score = scorecard(predictions, observed["rows"])
    k_data_for_sensitivity = dict(k_data)
    k_data_for_sensitivity["seed_level_map"] = {(row["ecology"], int(row["seed"]), int(row["k"])): np.asarray(row["K"], dtype=float) for row in k_data["seed_level"]}
    sensitivity = sensitivity_scorecards(k_data_for_sensitivity, observed["rows"])
    after = inventory()
    after["micro_raw_sha256_after"] = sha256_file(MICRO_RAW); after["macro_raw_sha256_after"] = sha256_file(MACRO_RAW)
    after["raw_hash_changes"] = [name for name in ("micro", "macro") if before[f"{name}_raw_sha256_before"] != after[f"{name}_raw_sha256_after"]]
    write_json(REPAIR_ROOT / "forensic_inventory_after.json", after)
    if after["raw_hash_changes"]: raise AssertionError("raw scientific files changed during repair")
    return {"inventory": before, "after": after, "k": k_data, "predictions": predictions, "observed": observed, "scorecard": score, "sensitivity": sensitivity}


if __name__ == "__main__":
    print(json.dumps(run_forensic_repair(), indent=2, default=_json_default))
