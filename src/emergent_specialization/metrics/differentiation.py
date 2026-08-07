"""Analysis-only measures of competence differentiation and routing alignment.

These functions operate on checkpoint summaries.  They never participate in
task generation, routing, feedback, or memory updates, so adding them cannot
change the scientific dynamics of a run.
"""

from __future__ import annotations

import itertools
from collections.abc import Mapping, Sequence
from typing import Any


def _rectangular_matrix(matrix: Sequence[Sequence[float]]) -> list[list[float]]:
    rows = [[float(value) for value in row] for row in matrix]
    if not rows:
        return []
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError("competence matrix must be rectangular")
    return rows


def competence_differentiation_phi(matrix: Sequence[Sequence[float]]) -> float:
    """Return ``Phi = (1/K) sum_c Var_i[A_ic]`` using population variance.

    ``Phi`` measures competence differentiation, not specialization or useful
    division of labor.  Empty or zero-column matrices return zero.
    """
    rows = _rectangular_matrix(matrix)
    if not rows or not rows[0]:
        return 0.0
    n_agents = len(rows)
    n_worlds = len(rows[0])
    total = 0.0
    for column in range(n_worlds):
        mean = sum(row[column] for row in rows) / n_agents
        total += sum((row[column] - mean) ** 2 for row in rows) / n_agents
    return total / n_worlds


def competence_differentiation_phi_from_mapping(
    competence: Mapping[str, Mapping[str, float]],
    *,
    agent_ids: Sequence[str] | None = None,
    worlds: Sequence[str] | None = None,
) -> float:
    """Compute ``Phi`` from the logged ``agent -> world -> accuracy`` mapping."""
    ids = tuple(agent_ids) if agent_ids is not None else tuple(sorted(competence))
    domain = tuple(worlds) if worlds is not None else tuple(
        sorted({world for profile in competence.values() for world in profile})
    )
    matrix = [[float(competence.get(agent, {}).get(world, 0.0)) for world in domain] for agent in ids]
    return competence_differentiation_phi(matrix)


def competence_spectral_differentiation(matrix: Sequence[Sequence[float]]) -> dict[str, Any]:
    """Return eigenvalues and participation ratio of competence differentiation.

    The matrix is centered across agents, ``Q = X Xᵀ / K`` is formed, and a
    small dependency-free Jacobi eigensolver is used.  This is an analysis-only
    effective dimensionality, not evidence of roles or specialization.
    """
    rows = _rectangular_matrix(matrix)
    if not rows or not rows[0]:
        return {"eigenvalues": [], "trace": 0.0, "participation_ratio": 0.0}
    n_agents = len(rows)
    n_worlds = len(rows[0])
    means = [sum(row[col] for row in rows) / n_agents for col in range(n_worlds)]
    centered = [[row[col] - means[col] for col in range(n_worlds)] for row in rows]
    matrix_q = [
        [sum(centered[i][col] * centered[j][col] for col in range(n_worlds)) / n_worlds for j in range(n_agents)]
        for i in range(n_agents)
    ]
    # Jacobi rotations are ample for the small N=4 competence matrices used by
    # this project and avoid introducing a numerical dependency for reports.
    for _ in range(max(1, 20 * n_agents * n_agents)):
        pivot_i, pivot_j = 0, 0
        largest = 0.0
        for i in range(n_agents):
            for j in range(i + 1, n_agents):
                value = abs(matrix_q[i][j])
                if value > largest:
                    largest, pivot_i, pivot_j = value, i, j
        if largest <= 1e-12:
            break
        app = matrix_q[pivot_i][pivot_i]
        aqq = matrix_q[pivot_j][pivot_j]
        apq = matrix_q[pivot_i][pivot_j]
        angle = 0.5 * __import__("math").atan2(2.0 * apq, aqq - app)
        cosine = __import__("math").cos(angle)
        sine = __import__("math").sin(angle)
        for k in range(n_agents):
            if k in {pivot_i, pivot_j}:
                continue
            aik = matrix_q[pivot_i][k]
            ajk = matrix_q[pivot_j][k]
            matrix_q[pivot_i][k] = matrix_q[k][pivot_i] = cosine * aik - sine * ajk
            matrix_q[pivot_j][k] = matrix_q[k][pivot_j] = sine * aik + cosine * ajk
        matrix_q[pivot_i][pivot_i] = cosine * cosine * app - 2.0 * sine * cosine * apq + sine * sine * aqq
        matrix_q[pivot_j][pivot_j] = sine * sine * app + 2.0 * sine * cosine * apq + cosine * cosine * aqq
        matrix_q[pivot_i][pivot_j] = matrix_q[pivot_j][pivot_i] = 0.0
    eigenvalues = sorted((max(0.0, matrix_q[i][i]) for i in range(n_agents)), reverse=True)
    trace = sum(eigenvalues)
    denominator = sum(value * value for value in eigenvalues)
    participation_ratio = (trace * trace / denominator) if denominator > 1e-15 else 0.0
    return {
        "eigenvalues": eigenvalues,
        "trace": trace,
        "participation_ratio": participation_ratio,
    }


def competence_spectral_differentiation_from_mapping(
    competence: Mapping[str, Mapping[str, float]],
    *,
    agent_ids: Sequence[str] | None = None,
    worlds: Sequence[str] | None = None,
) -> dict[str, Any]:
    ids = tuple(agent_ids) if agent_ids is not None else tuple(sorted(competence))
    domain = tuple(worlds) if worlds is not None else tuple(sorted({world for profile in competence.values() for world in profile}))
    matrix = [[float(competence.get(agent, {}).get(world, 0.0)) for world in domain] for agent in ids]
    return competence_spectral_differentiation(matrix)


def routing_alignment(
    routing_counts_by_world_agent: Mapping[str, Mapping[str, int | float]],
    competence: Mapping[str, Mapping[str, float]],
    *,
    world_priors: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Compare routed competence to random and domain-oracle baselines.

    ``eta_route`` is normalized to the interval where random routing is zero
    and per-domain oracle routing is one.  A negative value means routing is
    systematically worse than the random competence baseline.  If the oracle
    denominator is zero, ``eta_route`` is ``None`` rather than fabricated.
    """
    worlds = tuple(sorted(set(routing_counts_by_world_agent) | {world for profile in competence.values() for world in profile}))
    agents = tuple(sorted(set(competence) | {agent for row in routing_counts_by_world_agent.values() for agent in row}))
    if not worlds or not agents:
        return {"u_route": 0.0, "u_rand": 0.0, "u_oracle_domain": 0.0, "eta_route": None}
    weights = {world: float(world_priors.get(world, 0.0)) if world_priors else 1.0 for world in worlds}
    total_weight = sum(weights.values())
    if total_weight <= 0:
        raise ValueError("world priors must have positive total weight")
    weights = {world: value / total_weight for world, value in weights.items()}

    routed = random_baseline = oracle = 0.0
    for world in worlds:
        counts = {agent: float(routing_counts_by_world_agent.get(world, {}).get(agent, 0.0)) for agent in agents}
        total_routes = sum(counts.values())
        profile = {agent: float(competence.get(agent, {}).get(world, 0.0)) for agent in agents}
        if total_routes > 0:
            routed_world = sum((counts[agent] / total_routes) * profile[agent] for agent in agents)
        else:
            routed_world = sum(profile.values()) / len(agents)
        random_world = sum(profile.values()) / len(agents)
        routed += weights[world] * routed_world
        random_baseline += weights[world] * random_world
        oracle += weights[world] * max(profile.values())
    denominator = oracle - random_baseline
    eta = (routed - random_baseline) / denominator if denominator > 0 else None
    return {
        "u_route": routed,
        "u_rand": random_baseline,
        "u_oracle_domain": oracle,
        "eta_route": eta,
    }


def division_of_labor_matching(
    competence: Mapping[str, Mapping[str, float]],
    *,
    worlds: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Return the best one-agent-per-world matching for small matrices.

    This is an analysis-only, dependency-free exhaustive assignment.  It is
    intentionally limited to at most eight agents; larger studies should use
    a vetted assignment implementation explicitly.
    """
    agents = tuple(sorted(competence))
    domain = tuple(worlds) if worlds is not None else tuple(
        sorted({world for profile in competence.values() for world in profile})
    )
    if not agents or not domain:
        return {"u_match": 0.0, "u_single": 0.0, "delta_match": 0.0, "assignment": {}}
    if len(agents) != len(domain):
        raise ValueError("division_of_labor_matching requires equal agent and world counts")
    if len(agents) > 8:
        raise ValueError("division_of_labor_matching is limited to at most 8 agents")
    scores = {(agent, world): float(competence.get(agent, {}).get(world, 0.0)) for agent in agents for world in domain}
    best_value = -1.0
    best_assignment: tuple[str, ...] | None = None
    for permutation in itertools.permutations(agents):
        value = sum(scores[(agent, world)] for agent, world in zip(permutation, domain)) / len(domain)
        if value > best_value or (value == best_value and (best_assignment is None or permutation < best_assignment)):
            best_value = value
            best_assignment = permutation
    assert best_assignment is not None
    single = max(sum(scores[(agent, world)] for world in domain) / len(domain) for agent in agents)
    return {
        "u_match": best_value,
        "u_single": single,
        "delta_match": best_value - single,
        "assignment": {world: agent for world, agent in zip(domain, best_assignment)},
    }
