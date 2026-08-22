"""Mechanical Theory V1 prediction generation from measured K matrices."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from emergent_specialization.studies.theory.v1.dynamics import critical_beta, jacobian, spectral_summary_centered, classify_regime, transfer_operator
from emergent_specialization.studies.theory.v1.micro_design import ECOLOGIES, K_VALUES, macro_cells


def predictions_for_k(k_matrix: Sequence[Sequence[float]], k: int) -> list[dict[str, Any]]:
    rows = []
    for cell in macro_cells():
        if int(cell["k"]) != int(k):
            continue
        operator = jacobian(k_matrix, k, cell["q_share"], cell["beta"], cell["epsilon"])
        spectrum = spectral_summary_centered(operator)
        row = {**cell, "k_matrix": k, "r": float(operator[0, 0]) if cell["beta"] == 0 else None,
               "R_spec": spectrum["spectral_radius"], "lambda_pred": spectrum["lambda_spec"],
               "g_pred": 2.0 * spectrum["lambda_spec"], "regime": classify_regime(spectrum["spectral_radius"]),
               "dominant_mode": spectrum["dominant_mode"], "relative_spectral_gap": spectrum["relative_spectral_gap"],
               "beta_critical": critical_beta(k_matrix, k, cell["q_share"], cell["epsilon"]),
               "eigenvalues_real": spectrum["eigenvalues_real"], "eigenvalues_imag": spectrum["eigenvalues_imag"]}
        rows.append(row)
    if len(rows) != 5 + (3 if int(k) == 8 else 0):
        raise AssertionError(f"prediction cell/K mismatch for k={k}: {len(rows)} rows")
    baseline = next(row for row in rows if row["beta"] == 0.0 and row["q_share"] == 0.0 and row["epsilon"] == 0.10)
    for row in rows:
        row["g_excess_pred"] = float(row["g_pred"] - baseline["g_pred"])
    return rows


def build_prediction_registry(k_by_ecology: Mapping[str, Mapping[int, Sequence[Sequence[float]]]]) -> dict[str, Any]:
    rows = []
    for ecology in ECOLOGIES:
        for k in K_VALUES:
            if ecology not in k_by_ecology or k not in k_by_ecology[ecology]:
                raise ValueError(f"missing K for {ecology}/k={k}")
            for row in predictions_for_k(k_by_ecology[ecology][k], k):
                rows.append({"ecology": ecology, **row})
    return {"protocol": "THEORY-V1", "predictions": rows, "fitted_to_macro": False}
