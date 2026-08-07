"""Agent-label-invariant summaries and small-matrix alignment helpers."""

from __future__ import annotations

import itertools
import math
from typing import Mapping, Sequence

from .information import entropy


def routing_mass_order(routing_counts: Mapping[str, int | float]) -> tuple[str, ...]:
    """Order agents by decreasing routed mass, with an explicit label tie-break."""
    return tuple(sorted(routing_counts, key=lambda agent: (-float(routing_counts[agent]), str(agent))))


def competence_profile_order(
    profiles: Mapping[str, Mapping[str, float]], worlds: Sequence[str] | None = None
) -> tuple[str, ...]:
    """Canonical order by descending competence profile, independent of IDs."""
    world_order = tuple(worlds) if worlds is not None else tuple(sorted({world for row in profiles.values() for world in row}))
    return tuple(
        sorted(
            profiles,
            key=lambda agent: tuple(-float(profiles[agent].get(world, 0.0)) for world in world_order)
            + (str(agent),),
        )
    )


def sorted_profile_values(profiles: Mapping[str, Mapping[str, float]]) -> tuple[tuple[float, ...], ...]:
    """Return competence rows sorted lexicographically, omitting agent labels."""
    worlds = tuple(sorted({world for profile in profiles.values() for world in profile}))
    return tuple(
        sorted(tuple(float(profile.get(world, 0.0)) for world in worlds) for profile in profiles.values())
    )


def _alignment_cost(reference: Mapping[str, Mapping[str, float]], candidate: Mapping[str, Mapping[str, float]], ref: str, cand: str, worlds: Sequence[str]) -> float:
    return sum((float(reference[ref].get(world, 0.0)) - float(candidate[cand].get(world, 0.0))) ** 2 for world in worlds)


def align_competence_profiles(
    reference: Mapping[str, Mapping[str, float]], candidate: Mapping[str, Mapping[str, float]]
) -> tuple[dict[str, str], float]:
    """Find the minimum-cost candidate-to-reference assignment for small N.

    The implementation is deliberately dependency-free and refuses matrices
    larger than eight agents; larger studies should use a vetted assignment
    implementation explicitly rather than silently taking a factorial path.
    """
    reference_ids = tuple(sorted(reference))
    candidate_ids = tuple(sorted(candidate))
    if len(reference_ids) != len(candidate_ids):
        raise ValueError("reference and candidate must contain the same number of agents")
    if len(reference_ids) > 8:
        raise ValueError("brute-force alignment is limited to at most 8 agents")
    worlds = tuple(sorted({world for profiles in (reference, candidate) for row in profiles.values() for world in row}))
    best: tuple[float, tuple[str, ...]] | None = None
    for permutation in itertools.permutations(reference_ids):
        cost = sum(
            _alignment_cost(reference, candidate, reference_id, candidate_id, worlds)
            for reference_id, candidate_id in zip(permutation, candidate_ids)
        )
        key = (cost, permutation)
        if best is None or key < best:
            best = key
    assert best is not None
    _, permutation = best
    return {candidate_id: reference_id for candidate_id, reference_id in zip(candidate_ids, permutation)}, float(best[0])


def align_competence_matrix(
    reference: Mapping[str, Mapping[str, float]], candidate: Mapping[str, Mapping[str, float]]
) -> dict[str, dict[str, float]]:
    """Return candidate rows relabeled into the reference agent coordinate system."""
    mapping, _ = align_competence_profiles(reference, candidate)
    return {mapping[candidate_id]: dict(candidate[candidate_id]) for candidate_id in sorted(candidate)}


def within_run_asymmetry(profiles: Mapping[str, Mapping[str, float]]) -> float:
    """Mean pairwise Euclidean distance between competence profiles."""
    ids = tuple(sorted(profiles))
    if len(ids) < 2:
        return 0.0
    worlds = tuple(sorted({world for profile in profiles.values() for world in profile}))
    distances = []
    for left, right in itertools.combinations(ids, 2):
        distances.append(
            math.sqrt(
                sum(
                    (float(profiles[left].get(world, 0.0)) - float(profiles[right].get(world, 0.0))) ** 2
                    for world in worlds
                )
            )
        )
    return sum(distances) / len(distances)


def ensemble_symmetry_within_run_asymmetry(
    runs: Sequence[Mapping[str, Mapping[str, float]]]
) -> dict[str, float | None]:
    """Summarize within-run differentiation and across-run label symmetry.

    ``label_usage_entropy`` is the entropy of the label occupying the most
    competent world across runs. It is only a diagnostic; callers should report
    the assignment rule and sample size alongside it.
    """
    if not runs:
        return {"mean_within_run_asymmetry": None, "label_usage_entropy": 0.0, "normalized_label_usage_entropy": 0.0}
    asymmetry = [within_run_asymmetry(run) for run in runs]
    top_labels: list[str] = []
    for profiles in runs:
        for world in sorted({world for profile in profiles.values() for world in profile}):
            top_labels.append(max(profiles, key=lambda agent: (float(profiles[agent].get(world, 0.0)), str(agent))))
    label_entropy = entropy(top_labels)
    return {
        "mean_within_run_asymmetry": sum(asymmetry) / len(asymmetry),
        "label_usage_entropy": label_entropy,
        "normalized_label_usage_entropy": label_entropy / math.log2(len(set(top_labels))) if len(set(top_labels)) > 1 else 0.0,
    }


def role_profile_stability(
    profiles: Sequence[Mapping[str, Mapping[str, float]]], *, agent_id: str | None = None
) -> list[float]:
    """Cosine-like profile stability; caller chooses occupant or aligned role."""
    if len(profiles) < 2:
        return []
    if agent_id is None:
        raise ValueError("agent_id is required; role and occupant stability are distinct questions")
    worlds = tuple(sorted({world for snapshot in profiles for row in snapshot.values() for world in row}))
    vectors = [tuple(float(snapshot.get(agent_id, {}).get(world, 0.0)) for world in worlds) for snapshot in profiles]
    return [
        sum(a * b for a, b in zip(left, right))
        / (math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right)))
        if any(left) and any(right)
        else 0.0
        for left, right in zip(vectors, vectors[1:])
    ]
