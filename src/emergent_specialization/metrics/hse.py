"""Exact single-linkage Hierarchic Social Entropy over [0, 1]."""

from __future__ import annotations

import math
from typing import Sequence

from emergent_specialization.metrics.behavioral import pairwise_behavioral_distances


def _components_at_threshold(distances: Sequence[Sequence[float]], threshold: float) -> list[list[int]]:
    """Connected components of edges with distance <= h (single linkage)."""
    n = len(distances)
    parent = list(range(n))

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for left in range(n):
        for right in range(left + 1, n):
            if distances[left][right] <= threshold + 1e-12:
                union(left, right)
    groups: dict[int, list[int]] = {}
    for index in range(n):
        groups.setdefault(find(index), []).append(index)
    return list(groups.values())


def partition_entropy(clusters: Sequence[Sequence[int]], population_size: int) -> float:
    return max(
        0.0,
        -sum(
            (len(cluster) / population_size) * math.log2(len(cluster) / population_size)
            for cluster in clusters
        ),
    )


def hierarchic_social_entropy(matrix: Sequence[Sequence[int]]) -> dict[str, object]:
    """Integrate cluster-size entropy exactly over single-linkage merge intervals.

    Cosine distance lies in [0, 1].  For a threshold h, single-linkage clusters
    are the connected components under edges d <= h. The partition is constant
    between distinct merge heights, so summing entropy × interval width gives
    the integral without numerical quadrature.
    """
    n = len(matrix)
    if n == 0:
        return {"hse": 0.0, "normalized_hse": 0.0, "merge_heights": [], "distance_matrix": []}
    if n == 1:
        return {"hse": 0.0, "normalized_hse": 0.0, "merge_heights": [], "distance_matrix": [[0.0]]}
    distances = pairwise_behavioral_distances(matrix)
    candidate_heights = sorted(
        {0.0, 1.0, *(distances[left][right] for left in range(n) for right in range(left + 1, n))}
    )
    # Keep precisely the thresholds at which the single-linkage partition
    # changes, rather than every pairwise distance that happens not to produce
    # a dendrogram merge. Zero-distance merges occur at the lower boundary.
    heights = [0.0]
    previous_partition = sorted(sorted(cluster) for cluster in _components_at_threshold(distances, 0.0))
    for height in candidate_heights[1:-1]:
        partition = sorted(sorted(cluster) for cluster in _components_at_threshold(distances, height))
        if partition != previous_partition:
            heights.append(height)
            previous_partition = partition
    if heights[-1] != 1.0:
        heights.append(1.0)
    hse = 0.0
    intervals: list[dict[str, object]] = []
    for left, right in zip(heights, heights[1:]):
        if right <= left:
            continue
        clusters = _components_at_threshold(distances, left)
        entropy_value = partition_entropy(clusters, n)
        contribution = entropy_value * (right - left)
        hse += contribution
        intervals.append(
            {
                "start": left,
                "end": right,
                "cluster_sizes": sorted(len(cluster) for cluster in clusters),
                "entropy": entropy_value,
                "contribution": contribution,
            }
        )
    return {
        "hse": hse,
        "normalized_hse": hse / math.log2(n),
        "merge_heights": heights,
        "distance_matrix": distances,
        "intervals": intervals,
    }
