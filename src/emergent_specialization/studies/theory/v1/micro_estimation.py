"""Deterministic estimators for the local microscopic operator K."""

from __future__ import annotations

from typing import Sequence

import numpy as np


def _center_columns(values: np.ndarray) -> np.ndarray:
    projector = np.eye(values.shape[1]) - np.ones((values.shape[1], values.shape[1])) / values.shape[1]
    return values @ projector


def estimate_k_explicit(swaps: Sequence[Sequence[float]], contrasts: Sequence[Sequence[float]], n_niches: int = 4) -> np.ndarray:
    """Estimate row-source/column-target K with an explicit centered design.

    Each swap row is a source contrast ``e_c-e_r`` and each contrast row is the
    corresponding target competence response.  A pseudoinverse is the fixed,
    unregularized solution required by Theory V1.
    """
    design = np.asarray(swaps, dtype=float)
    response = np.asarray(contrasts, dtype=float)
    if design.ndim != 2 or design.shape[1] != n_niches or response.ndim != 2 or response.shape[0] != design.shape[0] or response.shape[1] != n_niches:
        raise ValueError("swaps and contrasts must be matching [observations,niches] arrays")
    design = _center_columns(design)
    response = _center_columns(response)
    # K has source rows and target columns, so response = design @ K.
    return np.linalg.pinv(design) @ response


def estimate_k_pairwise(swaps: Sequence[Sequence[float]], contrasts: Sequence[Sequence[float]], n_niches: int = 4) -> np.ndarray:
    """Independent direct reconstruction using centered basis coordinates."""
    design = np.asarray(swaps, dtype=float)
    response = _center_columns(np.asarray(contrasts, dtype=float))
    # Decode each ordered pair as a row difference K[target]-K[source], then
    # solve the graph potential with the fixed zero-row-sum gauge.  This does
    # not call the explicit design-matrix estimator above.
    equations = []
    for row in design:
        nonzero = np.flatnonzero(np.abs(row) > 1e-12)
        if len(nonzero) != 2:
            raise ValueError("pairwise reconstruction requires one-for-one swaps")
        source, target = int(nonzero[0]), int(nonzero[1])
        if row[source] > 0:
            source, target = target, source
        equation = np.zeros(n_niches, dtype=float)
        equation[target] = 1.0
        equation[source] = -1.0
        equations.append(equation)
    equations.append(np.ones(n_niches, dtype=float))
    lhs = np.asarray(equations)
    result = np.zeros((n_niches, n_niches), dtype=float)
    for column in range(n_niches):
        rhs = np.concatenate([response[:, column], [0.0]])
        result[:, column] = np.linalg.lstsq(lhs, rhs, rcond=None)[0]
    return _center_columns(result)


def superposition_diagnostics(observed: Sequence[Sequence[float]], predicted: Sequence[Sequence[float]]) -> dict[str, float]:
    actual = np.asarray(observed, dtype=float).ravel()
    estimate = np.asarray(predicted, dtype=float).ravel()
    if actual.shape != estimate.shape or not actual.size:
        raise ValueError("observed and predicted arrays must have equal non-zero size")
    residual = actual - estimate
    ss_total = float(np.sum((actual - actual.mean()) ** 2))
    r2 = 1.0 - float(np.sum(residual * residual)) / ss_total if ss_total > 0 else 1.0
    cosine = float(np.dot(actual, estimate) / (np.linalg.norm(actual) * np.linalg.norm(estimate))) if np.linalg.norm(actual) and np.linalg.norm(estimate) else 0.0
    return {"r2": r2, "cosine": cosine, "normalized_superposition_error": float(np.linalg.norm(residual) / (np.linalg.norm(actual) or 1.0))}
