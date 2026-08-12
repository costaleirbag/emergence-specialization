"""Pre-registered Theory V1 scorecard calculations."""

from __future__ import annotations

import itertools
from typing import Any, Sequence

import numpy as np


def _rank(values: Sequence[float]) -> np.ndarray:
    order = np.argsort(np.argsort(np.asarray(values, dtype=float), kind="mergesort"), kind="mergesort")
    return order.astype(float)


def spearman(x: Sequence[float], y: Sequence[float]) -> float:
    if len(x) != len(y) or len(x) < 2:
        raise ValueError("correlation requires equal vectors with at least two values")
    a, b = _rank(x), _rank(y)
    if np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def kendall_tau(x: Sequence[float], y: Sequence[float]) -> float:
    pairs = list(itertools.combinations(range(len(x)), 2))
    concordant = discordant = usable = 0
    for i, j in pairs:
        dx, dy = x[i] - x[j], y[i] - y[j]
        if dx == 0 or dy == 0:
            continue
        usable += 1
        concordant += int(dx * dy > 0)
        discordant += int(dx * dy < 0)
    return (concordant - discordant) / usable if usable else float("nan")


def pairwise_concordance(predicted: Sequence[float], observed: Sequence[float], margin: float = 0.002) -> dict[str, Any]:
    total = correct = 0
    for i, j in itertools.combinations(range(len(predicted)), 2):
        if abs(predicted[i] - predicted[j]) < margin:
            continue
        total += 1
        correct += int((predicted[i] - predicted[j]) * (observed[i] - observed[j]) > 0)
    return {"eligible": total, "correct": correct, "accuracy": correct / total if total else None, "status": "NON_IDENTIFIABLE" if total < 10 else ("PASS" if correct / total >= .75 else "FAIL")}


def score_t1(predicted: Sequence[float], observed: Sequence[float], ecology_slices: dict[str, tuple[int, int]]) -> dict[str, Any]:
    pooled = spearman(predicted, observed)
    per_ecology = {name: spearman(predicted[start:end], observed[start:end]) for name, (start, end) in ecology_slices.items()}
    passed = pooled >= .70 and all(value >= .50 for value in per_ecology.values())
    return {"pooled_spearman": pooled, "ecology_spearman": per_ecology, "status": "PASS" if passed else "FAIL"}

