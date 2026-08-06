"""Useful coverage metrics, separate from diversity itself."""

from __future__ import annotations

from typing import Sequence

from .behavioral import individual_accuracy


def complementarity_metrics(matrix: Sequence[Sequence[int]]) -> dict[str, float | list[float]]:
    accuracies = individual_accuracy(matrix)
    if not matrix or not matrix[0]:
        return {
            "individual_accuracy": accuracies,
            "best_individual_accuracy": 0.0,
            "oracle_society_accuracy": 0.0,
            "oracle_gain": 0.0,
        }
    width = len(matrix[0])
    oracle = sum(1 for index in range(width) if any(row[index] for row in matrix)) / width
    best = max(accuracies)
    return {
        "individual_accuracy": accuracies,
        "best_individual_accuracy": best,
        "oracle_society_accuracy": oracle,
        "oracle_gain": oracle - best,
    }
