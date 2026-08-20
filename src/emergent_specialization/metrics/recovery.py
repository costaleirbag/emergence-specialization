"""Simple recovery summaries for future ablation experiments."""

from __future__ import annotations

import math
from typing import Mapping, Sequence


def performance_recovery_time(
    values: Sequence[float], *, baseline: float | None = None, tolerance: float = 0.05, start_index: int = 0
) -> int | None:
    """First index at which a scalar returns within ``tolerance`` of baseline."""
    if not values:
        return None
    reference = float(values[start_index] if baseline is None else baseline)
    threshold = reference - abs(tolerance)
    return next((index for index, value in enumerate(values[start_index:], start_index) if value >= threshold), None)


def profile_distance(left: Mapping[str, float], right: Mapping[str, float]) -> float:
    worlds = sorted(set(left) | set(right))
    return math.sqrt(sum((float(left.get(world, 0.0)) - float(right.get(world, 0.0))) ** 2 for world in worlds))


def niche_recovery_time(
    pre_profiles: Mapping[str, Mapping[str, float]], post_profiles: Sequence[Mapping[str, Mapping[str, float]]], *, tolerance: float = 0.1
) -> int | None:
    """First post-ablation snapshot whose best per-world competence recovers."""
    worlds = sorted({world for profile in pre_profiles.values() for world in profile})
    target = {world: max(profile.get(world, 0.0) for profile in pre_profiles.values()) for world in worlds}
    for index, snapshot in enumerate(post_profiles):
        current = {world: max((profile.get(world, 0.0) for profile in snapshot.values()), default=0.0) for world in worlds}
        if all(current[world] >= target[world] - abs(tolerance) for world in worlds):
            return index
    return None


def role_replacement_time(
    routing: Sequence[Mapping[str, object]], *, removed_agent: str, world: str, start_index: int = 0
) -> int | None:
    """First routed replacement for a world after an agent is removed."""
    for index, row in enumerate(routing[start_index:], start_index):
        if row.get("world") == world and row.get("selected_agent") not in {None, removed_agent}:
            return index
    return None
