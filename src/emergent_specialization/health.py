"""Offline run-health accounting for separating infrastructure from data."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .analysis import load_run


def _classify_error(value: object, category: object = None) -> str:
    if category in {"rate_limit", "server_error", "overloaded", "transient_transport", "empty_content", "parse_error"}:
        return str(category)
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
    configured_checkpoints = experiment.get("checkpoints")
    checkpoints = len(configured_checkpoints) if isinstance(configured_checkpoints, (list, tuple)) else len(bundle.checkpoints)
    final = bundle.checkpoints[-1] if bundle.checkpoints else {}
    probe_count = int(final.get("probe_count", 0) or 0)
    if probe_count == 0:
        probe_path = config.get("logging", {}).get("probe_set_path") if isinstance(config.get("logging", {}), dict) else None
        if probe_path:
            try:
                payload = json.loads(Path(str(probe_path)).read_text(encoding="utf-8"))
                probe_count = len(payload.get("tasks", [])) if isinstance(payload, dict) else 0
            except (OSError, json.JSONDecodeError, TypeError):
                probe_count = 0
    return rounds * num_agents + checkpoints * probe_count * num_agents


def run_health(run_dir: str | Path) -> dict[str, Any]:
    """Summarize physical attempts and logical completion coverage.

    Policy is explicit and conservative: ``healthy`` means every expected
    logical completion succeeded without errors; ``warning`` means complete
    coverage but retries/errors or incomplete usage metadata occurred; any
    missing logical completion is ``invalid`` for paired scientific analysis.
    """
    bundle = load_run(run_dir, require_completed=False, require_checkpoints=False)
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
    errors = Counter(
        _classify_error(event.get("error"), event.get("error_category"))
        for event in inferences
        if event.get("error")
    )
    retries = sum(max(0, int(event.get("attempt", 0))) for event in inferences)
    latencies = [float(event["latency_s"]) for event in inferences if isinstance(event.get("latency_s"), (int, float))]
    usage_calls = sum(isinstance(event.get("token_usage"), dict) and bool(event.get("token_usage")) for event in inferences)
    coverage = successful_logical / expected if expected else 1.0
    usage_coverage = usage_calls / len(inferences) if inferences else 0.0
    if successful_logical < expected or bundle.summary.get("status") != "completed":
        flag = "invalid"
        classification = "INVALID / INCOMPLETE"
    elif errors or retries or usage_coverage < 1.0:
        # A recovered transient failure remains visible, but does not make a
        # scientifically complete run unusable by itself.
        flag = "healthy_recovered"
        classification = "HEALTHY / RECOVERED"
    else:
        flag = "healthy"
        classification = "HEALTHY / CLEAN"
    observed_cost = sum(
        float(event.get("observed_cost_usd") or 0.0)
        for event in inferences
        if isinstance(event.get("observed_cost_usd"), (int, float))
    )
    return {
        "schema_version": 1,
        "run_id": bundle.run_id,
        "condition": bundle.condition,
        "seed": bundle.seed,
        "status": bundle.summary.get("status"),
        "health_flag": flag,
        "health_classification": classification,
        "expected_logical_completions": expected,
        "successful_logical_completions": successful_logical,
        "missing_logical_completions": max(0, expected - successful_logical),
        "physical_attempts": len(inferences),
        "retries": retries,
        "timeout_count": errors["timeout"] + errors["transient_transport"],
        "parse_error_count": errors["parse_error"],
        "rate_limit_count": errors["rate_limit"],
        "server_error_count": errors["server_error"] + errors["overloaded"],
        "empty_content_count": errors["empty_content"],
        "other_error_count": errors["other_error"] + errors["provider_error"],
        "completion_coverage": coverage,
        "usage_calls": usage_calls,
        "usage_coverage": usage_coverage,
        "observed_cost_usd": observed_cost if observed_cost else None,
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
