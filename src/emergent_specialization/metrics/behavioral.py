"""Behavioral success vectors and per-domain competence."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Sequence

from ..models import Task


def behavioral_cosine_distance(a: Sequence[int], b: Sequence[int]) -> float:
    """Cosine distance with explicit zero-vector semantics from the plan."""
    if len(a) != len(b):
        raise ValueError("behavioral vectors must have equal length")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 and norm_b == 0:
        return 0.0
    if norm_a == 0 or norm_b == 0:
        return 1.0
    similarity = dot / (norm_a * norm_b)
    return max(0.0, min(1.0, 1.0 - similarity))


def pairwise_behavioral_distances(matrix: Sequence[Sequence[int]]) -> list[list[float]]:
    return [[behavioral_cosine_distance(left, right) for right in matrix] for left in matrix]


def individual_accuracy(matrix: Sequence[Sequence[int]]) -> list[float]:
    if not matrix:
        return []
    width = len(matrix[0])
    if width == 0:
        return [0.0 for _ in matrix]
    if any(len(row) != width for row in matrix):
        raise ValueError("behavioral matrix is ragged")
    return [sum(row) / width for row in matrix]


def competence_matrix(
    behavioral_matrix: Sequence[Sequence[int]], tasks: Sequence[Task], agent_ids: Sequence[str]
) -> dict[str, dict[str, float]]:
    if len(behavioral_matrix) != len(agent_ids):
        raise ValueError("matrix rows must match agent IDs")
    if any(len(row) != len(tasks) for row in behavioral_matrix):
        raise ValueError("matrix columns must match probe tasks")
    indices_by_world: dict[str, list[int]] = defaultdict(list)
    for index, task in enumerate(tasks):
        indices_by_world[task.world].append(index)
    result: dict[str, dict[str, float]] = {}
    for agent_id, row in zip(agent_ids, behavioral_matrix):
        result[agent_id] = {
            world: sum(row[index] for index in indices) / len(indices) for world, indices in indices_by_world.items()
        }
    return result
