"""Offline run-health accounting for separating infrastructure from data."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .analysis import load_run


def _classify_error(value: object) -> str:
    text = str(value or "").lower()
    if "timeout" in text:
        return "timeout"
    if "responseparseerror" in text or "parse" in text:
        return "parse_error"
    return "other_error"


def expected_logical_completions(bundle: Any) -> int:
    config = bundle.metadata.get("config", {})
    experiment = config.get("experiment", {})
    num_agents = int(experiment.get("num_agents", len(bundle.agent_ids)))
    rounds = int(experiment.get("num_rounds", len(bundle.events_of_type("round_complete"))))
    final = bundle.checkpoints[-1] if bundle.checkpoints else {}
    probe_count = int(final.get("probe_count", 0) or 0)
    checkpoints = len(bundle.checkpoints)
    return rounds * num_agents + checkpoints * probe_count * num_agents


def run_health(run_dir: str | Path) -> dict[str, Any]:
    """Summarize physical attempts and logical completion coverage.

    Policy is explicit and conservative: ``healthy`` means every expected
    logical completion succeeded without errors; ``warning`` means complete
    coverage but retries/errors or incomplete usage metadata occurred; any
    missing logical completion is ``invalid`` for paired scientific analysis.
    """
    bundle = load_run(run_dir)
    inferences = bundle.events_of_type("inference")
    expected = expected_logical_completions(bundle)
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for event in inferences:
        key = (
            event.get("phase"), event.get("round_id"), event.get("checkpoint"),
            event.get("probe_index"), event.get("agent_id"),
        )
        grouped.setdefault(key, []).append(event)
    successful_logical = sum(any(event.get("error") is None for event in attempts) for attempts in grouped.values())
    errors = Counter(_classify_error(event.get("error")) for event in inferences if event.get("error"))
    retries = sum(max(0, int(event.get("attempt", 0))) for event in inferences)
    latencies = [float(event["latency_s"]) for event in inferences if isinstance(event.get("latency_s"), (int, float))]
    usage_calls = sum(isinstance(event.get("token_usage"), dict) and bool(event.get("token_usage")) for event in inferences)
    coverage = successful_logical / expected if expected else 1.0
    usage_coverage = usage_calls / len(inferences) if inferences else 0.0
    if successful_logical < expected:
        flag = "invalid"
    elif errors or retries or usage_coverage < 1.0:
        flag = "warning"
    else:
        flag = "healthy"
    return {
        "schema_version": 1,
        "run_id": bundle.run_id,
        "condition": bundle.condition,
        "seed": bundle.seed,
        "status": bundle.summary.get("status"),
        "health_flag": flag,
        "expected_logical_completions": expected,
        "successful_logical_completions": successful_logical,
        "missing_logical_completions": max(0, expected - successful_logical),
        "physical_attempts": len(inferences),
        "retries": retries,
        "timeout_count": errors["timeout"],
        "parse_error_count": errors["parse_error"],
        "other_error_count": errors["other_error"],
        "completion_coverage": coverage,
        "usage_calls": usage_calls,
        "usage_coverage": usage_coverage,
        "latency_s": {
            "mean": statistics.fmean(latencies) if latencies else None,
            "median": statistics.median(latencies) if latencies else None,
            "min": min(latencies) if latencies else None,
            "max": max(latencies) if latencies else None,
        },
    }


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Summarize completed-run health offline")
    parser.add_argument("--run", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    print(json.dumps(run_health(args.run), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
