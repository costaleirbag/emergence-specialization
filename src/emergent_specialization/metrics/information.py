"""Entropy and task-domain / routed-agent mutual information."""

from __future__ import annotations

import math
import random
from collections import Counter
from typing import Hashable, Iterable, Sequence


def entropy(values: Iterable[Hashable]) -> float:
    counts = Counter(values)
    total = sum(counts.values())
    if total == 0:
        return 0.0
    # Avoid serializing/displaying the harmless IEEE ``-0.0`` for a collapsed
    # distribution, which is scientifically just zero entropy.
    return max(0.0, -sum((count / total) * math.log2(count / total) for count in counts.values()))


def utilization_entropy(selected_agents: Sequence[str]) -> float:
    return entropy(selected_agents)


def normalized_utilization_entropy(selected_agents: Sequence[str], num_agents: int) -> float:
    if num_agents <= 1:
        return 0.0
    return utilization_entropy(selected_agents) / math.log2(num_agents)


def mutual_information(worlds: Sequence[str], agents: Sequence[str]) -> float:
    if len(worlds) != len(agents):
        raise ValueError("worlds and agents must have the same length")
    total = len(worlds)
    if total == 0:
        return 0.0
    joint = Counter(zip(worlds, agents))
    world_counts = Counter(worlds)
    agent_counts = Counter(agents)
    return sum(
        (count / total)
        * math.log2((count * total) / (world_counts[world] * agent_counts[agent]))
        for (world, agent), count in joint.items()
    )


def normalized_mutual_information(worlds: Sequence[str], agents: Sequence[str]) -> float:
    domain_entropy = entropy(worlds)
    if domain_entropy == 0.0:
        return 0.0
    return mutual_information(worlds, agents) / domain_entropy


def permutation_mi_null(
    worlds: Sequence[str], agents: Sequence[str], *, permutations: int = 1000, seed: int = 0
) -> list[float]:
    """Generate a fixed-seed permutation null for routed-agent MI.

    This is a diagnostic for small samples, not a universal significance test.
    The world sequence remains fixed while routed labels are shuffled.
    """
    if permutations < 1:
        raise ValueError("permutations must be positive")
    if len(worlds) != len(agents):
        raise ValueError("worlds and agents must have the same length")
    rng = random.Random(seed)
    shuffled = list(agents)
    values: list[float] = []
    for _ in range(permutations):
        rng.shuffle(shuffled)
        values.append(mutual_information(worlds, shuffled))
    return values


def mi_null_diagnostic(
    worlds: Sequence[str], agents: Sequence[str], *, permutations: int = 1000, seed: int = 0
) -> dict[str, float | int | None]:
    """Return observed MI and a deterministic permutation-null diagnostic.

    The world/task sequence is held fixed while routed-agent labels are
    permuted. This is a finite-sample diagnostic, not a formal significance
    test. The null dispersion and 95th percentile are included explicitly so
    reports can show the measurement baseline rather than only a point value.
    """
    observed = mutual_information(worlds, agents)
    null = permutation_mi_null(worlds, agents, permutations=permutations, seed=seed)
    null_mean = sum(null) / len(null) if null else None
    percentile = (sum(value <= observed for value in null) / len(null)) if null else None
    null_std = math.sqrt(sum((value - null_mean) ** 2 for value in null) / len(null)) if null and null_mean is not None else None
    ordered = sorted(null)
    index = min(len(ordered) - 1, max(0, math.ceil(0.95 * len(ordered)) - 1)) if ordered else None
    null_95 = ordered[index] if index is not None else None
    domain_entropy = entropy(worlds)
    normalized_observed = observed / domain_entropy if domain_entropy > 0 else 0.0
    normalized_null = [value / domain_entropy for value in null] if domain_entropy > 0 else [0.0 for _ in null]
    normalized_null_mean = sum(normalized_null) / len(normalized_null) if normalized_null else None
    normalized_null_std = math.sqrt(sum((value - normalized_null_mean) ** 2 for value in normalized_null) / len(normalized_null)) if normalized_null and normalized_null_mean is not None else None
    normalized_ordered = sorted(normalized_null)
    normalized_null_95 = normalized_ordered[index] if index is not None else None
    return {
        "observed_mi": observed,
        "normalized_observed_mi": normalized_observed,
        "null_mean": null_mean,
        "null_std": null_std,
        "null_95th_percentile": null_95,
        "excess_mi": observed - null_mean if null_mean is not None else None,
        "null_percentile": percentile,
        "normalized_null_mean": normalized_null_mean,
        "normalized_null_std": normalized_null_std,
        "normalized_null_95th_percentile": normalized_null_95,
        "normalized_excess_mi": normalized_observed - normalized_null_mean if normalized_null_mean is not None else None,
        "permutations": permutations,
        "seed": seed,
    }
