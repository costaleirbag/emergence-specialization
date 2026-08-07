"""Cheap trajectory observables reconstructed from interaction events.

These metrics deliberately do not inspect probe responses. They are therefore
safe candidates for an online or multi-fidelity controller, while remaining
recomputable from immutable ``events.jsonl`` files.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence

from .information import mi_null_diagnostic, normalized_mutual_information, normalized_utilization_entropy


def gini(values: Sequence[float]) -> float:
    """Return the population Gini coefficient, with zero for an empty vector."""
    if not values:
        return 0.0
    ordered = sorted(max(0.0, float(value)) for value in values)
    total = sum(ordered)
    if total == 0.0:
        return 0.0
    n = len(ordered)
    return sum((2 * index - n - 1) * value for index, value in enumerate(ordered, 1)) / (n * total)


def _mean(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _variance(values: Sequence[float]) -> float | None:
    if not values:
        return None
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values) / len(values)


def online_observables(
    events: Iterable[dict[str, Any]], *, num_agents: int | None = None, rolling_window: int = 5,
    mi_permutations: int | None = None, mi_min_samples: int = 8, mi_seed: int = 0,
) -> list[dict[str, Any]]:
    """Build one cheap macrostate row after each completed interaction round.

    ``rolling_window`` affects only rolling accuracy; cumulative quantities are
    always computed from round one through the current round. Missing candidate
    responses are excluded from confidence summaries rather than imputed.
    """
    if rolling_window < 1:
        raise ValueError("rolling_window must be positive")
    if mi_permutations is not None and mi_permutations < 1:
        raise ValueError("mi_permutations must be positive when supplied")
    rounds = sorted(
        (event for event in events if event.get("event") == "round_complete"),
        key=lambda event: int(event["round"]),
    )
    if not rounds:
        return []
    agent_ids = sorted(
        {
            str(agent_id)
            for event in rounds
            for agent_id in (event.get("candidates", {}) or {}).keys()
        }
    )
    if num_agents is None:
        num_agents = len(agent_ids)
    if num_agents < 1:
        raise ValueError("num_agents must be positive")

    worlds: list[str] = []
    selected: list[str] = []
    correctness: list[float] = []
    confidence_values: list[float] = []
    memory_counts = {agent_id: 0 for agent_id in agent_ids}
    routing_counts = Counter()
    rows: list[dict[str, Any]] = []
    previous_agent: str | None = None

    for event in rounds:
        round_id = int(event["round"])
        task = event.get("task", {}) or {}
        world = str(task.get("world", "unknown"))
        selected_agent = event.get("selected_agent_id")
        if selected_agent is None:
            continue
        selected_agent = str(selected_agent)
        worlds.append(world)
        selected.append(selected_agent)
        correct = bool(event.get("selected_correct", False))
        correctness.append(float(correct))
        routing_counts[selected_agent] += 1
        recipients = [str(value) for value in event.get("feedback_recipients", [])]
        for recipient in recipients:
            memory_counts[recipient] = memory_counts.get(recipient, 0) + 1

        candidates = event.get("candidates", {}) or {}
        confidences = [
            float(candidate["confidence"])
            for candidate in candidates.values()
            if isinstance(candidate, dict) and candidate.get("confidence") is not None
        ]
        selected_candidate = candidates.get(selected_agent, {}) if isinstance(candidates, dict) else {}
        selected_confidence = selected_candidate.get("confidence") if isinstance(selected_candidate, dict) else None
        sorted_confidences = sorted(confidences, reverse=True)
        margin = sorted_confidences[0] - sorted_confidences[1] if len(sorted_confidences) >= 2 else None
        recent = correctness[-rolling_window:]
        total_routes = sum(routing_counts.values())
        route_distribution = {
            agent_id: routing_counts.get(agent_id, 0) / total_routes for agent_id in agent_ids
        }
        switch = previous_agent is not None and selected_agent != previous_agent
        previous_agent = selected_agent
        row = {
            "phase": "online",
            "round": round_id,
            "world": world,
            "selected_agent": selected_agent,
            "selected_correct": correct,
            "cumulative_accuracy": sum(correctness) / len(correctness),
            "rolling_accuracy": sum(recent) / len(recent),
            "mean_candidate_confidence": _mean(confidences),
            "candidate_confidence_variance": _variance(confidences),
            "selected_confidence": float(selected_confidence) if selected_confidence is not None else None,
            "confidence_margin": margin,
            "routing_counts": dict(routing_counts),
            "routing_distribution": route_distribution,
            "normalized_utilization_entropy": normalized_utilization_entropy(selected, num_agents),
            "routing_concentration": max(route_distribution.values(), default=0.0),
            "effective_utilized_agents": (
                2 ** (-sum(p * math.log2(p) for p in route_distribution.values() if p > 0))
                if route_distribution
                else 0.0
            ),
            "normalized_task_agent_mutual_information": normalized_mutual_information(worlds, selected),
            "memory_counts": dict(memory_counts),
            "memory_total": sum(memory_counts.values()),
            "memory_gini": gini(list(memory_counts.values())),
            "selected_agent_switch": switch,
            "selected_agent_switch_rate": sum(
                1 for before, after in zip(selected, selected[1:]) if before != after
            )
            / max(1, len(selected) - 1),
        }
        if mi_permutations is not None and len(worlds) >= mi_min_samples:
            row["mi_null_diagnostic"] = mi_null_diagnostic(
                worlds, selected, permutations=mi_permutations, seed=mi_seed
            )
        rows.append(row)
    return rows


def write_online_metrics(
    run_dir: str | Path, output: str | Path | None = None, *, rolling_window: int = 5,
    mi_permutations: int | None = None, mi_min_samples: int = 8, mi_seed: int = 0,
) -> Path:
    """Read a run's raw events and write a derived JSONL trajectory."""
    root = Path(run_dir)
    events = [
        json.loads(line)
        for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    configured_agents = metadata.get("config", {}).get("experiment", {}).get("num_agents")
    rows = online_observables(
        events,
        num_agents=int(configured_agents) if configured_agents else None,
        rolling_window=rolling_window,
        mi_permutations=mi_permutations,
        mi_min_samples=mi_min_samples,
        mi_seed=mi_seed,
    )
    destination = Path(output) if output is not None else root / "online_metrics.jsonl"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    return destination


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Derive cheap online observables from a completed run")
    parser.add_argument("--run", required=True, help="Completed run directory")
    parser.add_argument("--output", help="Output JSONL path (default: <run>/online_metrics.jsonl)")
    parser.add_argument("--rolling-window", type=int, default=5)
    parser.add_argument("--mi-permutations", type=int, help="Optional seeded MI null permutations")
    parser.add_argument("--mi-min-samples", type=int, default=8)
    parser.add_argument("--mi-seed", type=int, default=0)
    args = parser.parse_args(list(argv) if argv is not None else None)
    destination = write_online_metrics(
        args.run,
        args.output,
        rolling_window=args.rolling_window,
        mi_permutations=args.mi_permutations,
        mi_min_samples=args.mi_min_samples,
        mi_seed=args.mi_seed,
    )
    print(f"Wrote online trajectory: {destination}")


if __name__ == "__main__":
    main()
