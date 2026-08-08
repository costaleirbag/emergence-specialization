"""Transfer-geometry mathematics and the explicitly stated toy dynamics.

The functions in this module are analysis-only.  They do not alter the LLM
experiment and make no claim about DeepSeek internals.  ``L`` is always indexed
SOURCE x TARGET; the transpose appears explicitly in the learning operator.
"""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np


def projection(k: int) -> np.ndarray:
    if k < 2:
        raise ValueError("contrast projection requires k >= 2")
    identity = np.eye(k, dtype=float)
    return identity - np.ones((k, k), dtype=float) / k


def centered_transfer(L: Iterable[Iterable[float]], rho: Iterable[float] | None = None) -> np.ndarray:
    matrix = np.asarray(L, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("L must be a square SOURCE x TARGET matrix")
    k = matrix.shape[0]
    weights = np.ones(k, dtype=float) / k if rho is None else np.asarray(list(rho), dtype=float)
    if weights.shape != (k,) or np.any(weights < 0) or not math.isclose(float(weights.sum()), 1.0, abs_tol=1e-10):
        raise ValueError("rho must be a non-negative probability vector")
    P = projection(k)
    return P @ matrix.T @ np.diag(weights) @ P


def geometry_metrics(L: Iterable[Iterable[float]], rho: Iterable[float] | None = None) -> dict[str, float]:
    matrix = np.asarray(L, dtype=float)
    k = matrix.shape[0]
    T = centered_transfer(matrix, rho)
    diagonal = np.diag(matrix)
    off = matrix[~np.eye(k, dtype=bool)]
    singular = np.linalg.svd(T, compute_uv=False)
    nonzero = singular[singular > 1e-12]
    symmetric = (matrix + matrix.T) / 2
    symmetric_T = (T + T.T) / 2
    denom = float(np.linalg.norm(T + T.T, "fro"))
    eigenvalues = np.linalg.eigvals(T)
    return {
        "D": float(np.mean(diagonal)),
        "O": float(np.mean(off)),
        "Q": float(np.mean(diagonal) - np.mean(off)),
        "E_T": float(np.linalg.norm(T, "fro")),
        "chi": float(np.max(np.real(eigenvalues))),
        "r_eff": float(nonzero.sum() ** 2 / np.square(nonzero).sum()) if len(nonzero) else 0.0,
        "A_dir": float(np.linalg.norm(T - T.T, "fro") / denom) if denom else 0.0,
        "raw_mean": float(np.mean(matrix)),
        "symmetric_norm": float(np.linalg.norm(symmetric, "fro")),
        "symmetric_centered_norm": float(np.linalg.norm(symmetric_T, "fro")),
    }


def block_matrix(d: float, w: float, c: float) -> np.ndarray:
    if not d > w > c:
        raise ValueError("block matrix requires d > w > c")
    return np.array([[d, w, c, c], [w, d, c, c], [c, c, d, w], [c, c, w, d]], dtype=float)


def block_modes(d: float, w: float, c: float) -> dict[str, float]:
    """Eigenvalues of L_block and of T(L_block) for uniform rho."""
    return {
        "constant_L": d + w + 2 * c,
        "block_L": d + w - 2 * c,
        "within_L": d - w,
        "constant_T": 0.0,
        "block_T": (d + w - 2 * c) / 4.0,
        "within_T": (d - w) / 4.0,
    }


def flat_limit(alpha: float, k: int = 4) -> np.ndarray:
    return np.full((k, k), float(alpha))


def diagonal_limit(q: float, k: int = 4) -> np.ndarray:
    return np.eye(k, dtype=float) * float(q)


def toy_rhs(a: np.ndarray, L: np.ndarray, *, beta: float, eta: float, gamma: float,
            rho: np.ndarray | None = None) -> np.ndarray:
    """Right-hand side of the stated finite-N effective dynamics."""
    state = np.asarray(a, dtype=float)
    if state.ndim != 2:
        raise ValueError("a must have shape (N,K)")
    N, K = state.shape
    matrix = np.asarray(L, dtype=float)
    if matrix.shape != (K, K):
        raise ValueError("L shape must match competence dimension")
    frequencies = np.ones(K, dtype=float) / K if rho is None else np.asarray(rho, dtype=float)
    probabilities = np.empty((N, K), dtype=float)
    for c in range(K):
        logits = beta * state[:, c]
        logits -= np.max(logits)
        weights = np.exp(logits)
        probabilities[:, c] = weights / weights.sum()
    experiences = probabilities * frequencies[None, :]
    P = projection(K)
    gains = np.empty_like(state)
    for i in range(N):
        gains[i] = P @ matrix.T @ experiences[i]
    return eta * gains - gamma * state


def analytical_jacobian(L: Iterable[Iterable[float]], *, N: int, beta: float, eta: float,
                        gamma: float, rho: Iterable[float] | None = None) -> np.ndarray:
    matrix = np.asarray(L, dtype=float)
    K = matrix.shape[0]
    frequencies = np.ones(K, dtype=float) / K if rho is None else np.asarray(list(rho), dtype=float)
    P = projection(K)
    # Full finite-difference Jacobian: softmax couples agents at each niche,
    # while P is applied after the transfer gain.  Restricting inputs to the
    # niche-contrast subspace adds the right-hand P and yields T(L).
    B = (eta * beta / N) * (P @ matrix.T @ np.diag(frequencies))
    identity = np.eye(K)
    result = np.zeros((N * K, N * K), dtype=float)
    for i in range(N):
        for j in range(N):
            block = B - gamma * identity if i == j else np.zeros_like(B)
            block = block - B / N
            result[i * K:(i + 1) * K, j * K:(j + 1) * K] = block
    return result


def finite_difference_jacobian(a: np.ndarray, L: np.ndarray, *, beta: float, eta: float,
                               gamma: float, rho: np.ndarray | None = None, eps: float = 1e-7) -> np.ndarray:
    state = np.asarray(a, dtype=float)
    flat = state.reshape(-1)
    base = toy_rhs(state, L, beta=beta, eta=eta, gamma=gamma, rho=rho).reshape(-1)
    result = np.zeros((len(flat), len(flat)), dtype=float)
    for j in range(len(flat)):
        plus = flat.copy(); minus = flat.copy()
        plus[j] += eps; minus[j] -= eps
        result[:, j] = (toy_rhs(plus.reshape(state.shape), L, beta=beta, eta=eta, gamma=gamma, rho=rho).reshape(-1)
                        - toy_rhs(minus.reshape(state.shape), L, beta=beta, eta=eta, gamma=gamma, rho=rho).reshape(-1)) / (2 * eps)
    # The mathematical Jacobian is the across-agent perturbation block.  The
    # full RHS additionally contains a population-mean mode.  Returning the
    # full finite-difference matrix lets callers verify both explicitly.
    _ = base
    return result


def susceptibility(L: Iterable[Iterable[float]], rho: Iterable[float] | None = None) -> float:
    return geometry_metrics(L, rho)["chi"]


def rayleigh(matrix: Iterable[Iterable[float]], vector: Iterable[float]) -> float:
    M = np.asarray(matrix, dtype=float)
    v = np.asarray(list(vector), dtype=float)
    norm = np.linalg.norm(v)
    if norm == 0:
        raise ValueError("vector must be nonzero")
    v = v / norm
    return float(v @ M @ v)
