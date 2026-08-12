"""Theory V1 frozen equations.

The equations here are an explicit effective model, not an assertion about the
internal Jacobian of an LLM society.  All arrays use agents on rows and niches
on columns unless stated otherwise.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

import numpy as np


def centered_projector(size: int) -> np.ndarray:
    if size < 1:
        raise ValueError("projector size must be positive")
    identity = np.eye(size, dtype=float)
    return identity - np.ones((size, size), dtype=float) / size


def competence_interaction(matrix: Sequence[Sequence[float]]) -> np.ndarray:
    """Return the frozen double-centered agent×niche interaction Z."""
    values = np.asarray(matrix, dtype=float)
    if values.ndim != 2 or values.shape[0] < 2 or values.shape[1] < 2:
        raise ValueError("competence matrix must be a 2-D array with at least 2×2 entries")
    return centered_projector(values.shape[0]) @ values @ centered_projector(values.shape[1])


def psi_spec(matrix: Sequence[Sequence[float]]) -> float:
    z = competence_interaction(matrix)
    return float(np.sum(z * z) / z.size)


def retention(k: int, q_share: float, n_agents: int = 4) -> float:
    """Frozen mean-field FIFO retention r(k,q)=1-u(q)/k."""
    if k < 1 or n_agents < 2:
        raise ValueError("k and n_agents must be positive; n_agents must be at least 2")
    if not 0.0 <= q_share <= 1.0:
        raise ValueError("q_share must be in [0,1]")
    update_probability = q_share + (1.0 - q_share) / n_agents
    return 1.0 - update_probability / k


def transfer_operator(k_matrix: Sequence[Sequence[float]], rho: Sequence[float] | None = None) -> np.ndarray:
    """Compute T_k=P Kᵀ D_rho P on the niche-centered subspace."""
    values = np.asarray(k_matrix, dtype=float)
    if values.ndim != 2 or values.shape[0] != values.shape[1] or values.shape[0] < 2:
        raise ValueError("K must be a square matrix with at least 2 niches")
    size = values.shape[0]
    weights = np.ones(size, dtype=float) / size if rho is None else np.asarray(rho, dtype=float)
    if weights.shape != (size,) or np.any(weights < 0) or not math.isclose(float(weights.sum()), 1.0, abs_tol=1e-12):
        raise ValueError("rho must be a non-negative probability vector")
    projector = centered_projector(size)
    return projector @ values.T @ np.diag(weights) @ projector


def jacobian(k_matrix: Sequence[Sequence[float]], k: int, q_share: float, beta: float, epsilon: float, n_agents: int = 4, rho: Sequence[float] | None = None) -> np.ndarray:
    """Frozen J=rI+(1-q)(1-eps)beta/N*T_k."""
    if not 0.0 <= epsilon <= 1.0:
        raise ValueError("epsilon must be in [0,1]")
    if beta < 0:
        raise ValueError("beta must be non-negative")
    return retention(k, q_share, n_agents) * np.eye(len(k_matrix)) + (1.0 - q_share) * ((1.0 - epsilon) * beta / n_agents) * transfer_operator(k_matrix, rho)


def spectral_summary(operator: Sequence[Sequence[float]], tolerance: float = 1e-10) -> dict[str, Any]:
    values = np.asarray(operator, dtype=float)
    eigenvalues, eigenvectors = np.linalg.eig(values)
    # The centered subspace has one numerical zero eigenvalue.  Do not use it
    # to define a dominant niche mode.
    relevant = [index for index, value in enumerate(eigenvalues) if abs(value) > tolerance]
    if not relevant:
        relevant = list(range(len(eigenvalues)))
    order = sorted(relevant, key=lambda index: (float(eigenvalues[index].real), float(abs(eigenvalues[index])), -index), reverse=True)
    dominant = order[0]
    magnitudes = sorted((float(abs(eigenvalues[index])) for index in relevant), reverse=True)
    radius = max(float(abs(eigenvalues[index])) for index in relevant)
    second = magnitudes[1] if len(magnitudes) > 1 else 0.0
    gap = (radius - second) / radius if radius > tolerance else 0.0
    vector = np.asarray(eigenvectors[:, dominant].real, dtype=float)
    vector /= np.linalg.norm(vector) or 1.0
    return {
        "eigenvalues_real": [float(value.real) for value in eigenvalues],
        "eigenvalues_imag": [float(value.imag) for value in eigenvalues],
        "spectral_radius": radius,
        "lambda_spec": math.log(radius) if radius > 0 else float("-inf"),
        "dominant_mode": vector.tolist(),
        "relative_spectral_gap": gap,
        "non_normal_numerical_abscissa": float(np.max(np.linalg.eigvalsh((values + values.T) / 2.0))),
    }


def critical_beta(k_matrix: Sequence[Sequence[float]], k: int, q_share: float, epsilon: float, n_agents: int = 4, rho: Sequence[float] | None = None) -> float | None:
    """Scalar beta_c when the relevant real eigenvalue is positive.

    Returning None is intentional for q=1 or non-positive/degenerate chi;
    Theory V1 does not force a finite threshold in those cases.
    """
    if q_share == 1.0 or epsilon == 1.0:
        return None
    t = transfer_operator(k_matrix, rho)
    spectrum = spectral_summary(t)
    chi = max(spectrum["eigenvalues_real"])
    if chi <= 0:
        return None
    return n_agents * (1.0 - retention(k, q_share, n_agents)) / ((1.0 - q_share) * (1.0 - epsilon) * chi)


def classify_regime(spectral_radius: float) -> str:
    if spectral_radius <= 0.98:
        return "SUBCRITICAL"
    if spectral_radius < 1.02:
        return "TRANSITIONAL"
    return "SUPERCRITICAL"

