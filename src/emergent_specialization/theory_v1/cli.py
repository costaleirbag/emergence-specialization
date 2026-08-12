"""Offline Theory V1 preparation and mock validation CLI.

The real provider stages are deliberately not implemented as an implicit
fallback.  ``prepare`` writes only manifests; ``mock`` exercises equations.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .dynamics import jacobian, psi_spec, spectral_summary
from .micro_design import macro_cells, micro_manifest, expected_call_counts
from .micro_estimation import estimate_k_explicit, estimate_k_pairwise
from .prediction import build_prediction_registry


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "reports/theory-v1"


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def prepare() -> dict[str, object]:
    counts = expected_call_counts()
    manifest = micro_manifest()
    manifest.update({"macro_cells_per_ecology_seed": len(macro_cells()), "status": "PREPARED_OFFLINE", "paid_calls": 0})
    _write(OUT / "data_ledger.json", {"protocol": "THEORY-V1", "legacy": "DEVELOPMENT", "micro": "PARAMETERIZATION", "macro": "CONFIRMATORY", "status": "prepared"})
    _write(OUT / "micro_manifest.json", manifest)
    return {"status": "PREPARED_OFFLINE", "expected_calls": counts, "output": str(OUT)}


def mock() -> dict[str, object]:
    # K with a clear niche-specific contrast and a centered gauge.
    known = np.array([[.8, .1, .0, .1], [.1, .8, .1, .0], [.0, .1, .8, .1], [.1, .0, .1, .8]])
    projector = np.eye(4) - np.ones((4, 4)) / 4
    known = projector @ known @ projector
    swaps = []
    responses = []
    for source in range(4):
        for target in range(4):
            if source == target:
                continue
            delta = np.eye(4)[target] - np.eye(4)[source]
            swaps.append(delta)
            responses.append(delta @ known)
    explicit = estimate_k_explicit(swaps, responses)
    direct = estimate_k_pairwise(swaps, responses)
    agreement = float(np.max(np.abs(explicit - direct)))
    j0 = jacobian(explicit, 8, 0.0, 0.0, .10)
    j12 = jacobian(explicit, 8, 0.0, 12.0, .10)
    result = {"status": "MOCK_DATA_NOT_SCIENTIFIC_RESULT", "k_max_abs_error": float(np.max(np.abs(explicit - known))), "estimators_max_abs_difference": agreement, "psi_specialist_fixture": psi_spec(np.eye(4)), "beta0_spectral_radius": spectral_summary(j0)["spectral_radius"], "beta12_spectral_radius": spectral_summary(j12)["spectral_radius"]}
    _write(OUT / "mock_validation.json", result)
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Theory V1 offline preparation")
    parser.add_argument("stage", choices=("prepare", "mock"))
    args = parser.parse_args(argv)
    print(json.dumps(prepare() if args.stage == "prepare" else mock(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

