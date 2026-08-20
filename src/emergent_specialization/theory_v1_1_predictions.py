"""Offline, sealed Theory V1.1 prediction generation from fresh MICRO K."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from .theory_v1.dynamics import transfer_operator
from .theory_v1.forensic_repair import centered_spectrum
from .theory_v1_1 import (
    DATA_ROOT,
    HARD_CAP_USD,
    MACRO_CELLS_V11,
    MODEL,
    PROTOCOL,
    REPORT_ROOT,
    stable_hash,
)

PREDICTION_ROOT = REPORT_ROOT / "predictions"
PREDICTION_PATH = PREDICTION_ROOT / "prediction_manifest.json"
MICRO_K_PATH = REPORT_ROOT / "micro" / "k_reconstruction.json"
MICRO_MANIFEST_PATH = REPORT_ROOT / "micro_manifest.json"
MICRO_EVENTS_PATH = DATA_ROOT / "micro_events.jsonl"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_predictions() -> dict[str, Any]:
    if not MICRO_K_PATH.exists():
        raise RuntimeError("V1.1 MICRO K reconstruction is missing")
    reconstruction = json.loads(MICRO_K_PATH.read_text(encoding="utf-8"))
    pooled = reconstruction.get("pooled")
    if not isinstance(pooled, dict):
        raise RuntimeError("MICRO pooled K is missing")
    rows: list[dict[str, Any]] = []
    for ecology, k_values in sorted(pooled.items()):
        if "8" not in k_values:
            raise RuntimeError(f"V1.1 MICRO K8 missing for {ecology}")
        matrix = np.asarray(k_values["8"], dtype=float)
        baseline = centered_spectrum(matrix, 8, 0.0, 0.10, 0.0)
        k_hash = stable_hash(matrix.tolist())
        t_hash = stable_hash(np.asarray(transfer_operator(matrix), dtype=float).tolist())
        for cell in MACRO_CELLS_V11:
            spec = centered_spectrum(matrix, int(cell["k"]), float(cell["beta"]), float(cell["epsilon"]), float(cell["q_share"]))
            row = {
                "ecology": ecology,
                **cell,
                "K_identifier": f"{ecology}:pooled_fresh_v11:k8",
                "K_hash": k_hash,
                "T_hash": t_hash,
                "J_hash": stable_hash(spec["J_full"]),
                "R_spec": spec["R_spec"],
                "lambda_pred": spec["lambda_spec"],
                "g_pred": spec["g_pred"],
                "g_excess_pred": float(spec["g_pred"] - baseline["g_pred"]),
                "regime": spec.get("regime") or ("SUBCRITICAL" if spec["R_spec"] <= 0.98 else "TRANSITIONAL" if spec["R_spec"] < 1.02 else "SUPERCRITICAL"),
                "beta_critical": spec.get("beta_critical"),
                "dominant_mode": spec.get("dominant_mode"),
                "relative_spectral_gap": spec.get("relative_spectral_gap"),
                "centered_eigenvalues_real": spec.get("centered_eigenvalues_real"),
                "centered_eigenvalues_imag": spec.get("centered_eigenvalues_imag"),
            }
            if int(row["k"]) != 8:
                raise AssertionError("V1.1 prediction k/K mismatch")
            rows.append(row)
    expected = len(pooled) * len(MACRO_CELLS_V11)
    if expected != 16 or len(rows) != expected:
        raise AssertionError(f"V1.1 prediction cardinality {len(rows)} != {expected}")
    keys = [(r["ecology"], r["cell_id"]) for r in rows]
    if len(set(keys)) != len(keys):
        raise AssertionError("duplicate V1.1 prediction keys")
    payload = {
        "protocol": PROTOCOL,
        "status": "PREDICTIONS_GENERATED_AFTER_MICRO",
        "mathematical_specification": "Theory V1 equations frozen prospectively; V1.1 predictions sealed after fresh MICRO",
        "fitted_to_macro": False,
        "provider": "DeepSeek Direct",
        "model": MODEL,
        "thinking": "off",
        "hard_cap_usd": HARD_CAP_USD,
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPORT_ROOT.parents[1], text=True).strip(),
        "micro_manifest_sha256": _sha256(MICRO_MANIFEST_PATH),
        "micro_events_sha256": _sha256(MICRO_EVENTS_PATH),
        "prediction_rows": rows,
    }
    payload["manifest_hash"] = stable_hash(payload)
    if PREDICTION_PATH.exists():
        old = json.loads(PREDICTION_PATH.read_text(encoding="utf-8"))
        if old != payload:
            raise RuntimeError("existing V1.1 prediction seal differs; refusing overwrite")
        return old
    PREDICTION_ROOT.mkdir(parents=True, exist_ok=True)
    PREDICTION_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true")
    args = parser.parse_args()
    if args.build:
        print(json.dumps(build_predictions(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
