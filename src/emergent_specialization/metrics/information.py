"""Entropy and task-domain / routed-agent mutual information."""

from __future__ import annotations

import math
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
