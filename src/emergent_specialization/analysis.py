"""Read-only analysis layer over immutable experiment run artifacts.

This module deliberately depends only on the standard library.  It validates
and reshapes raw JSON/JSONL into records that notebooks and other report
frontends can consume without reimplementing scientific logic in cells.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from .costs import normalize_token_usage, summarize_usage

REQUIRED_RUN_FILES = ("metadata.json", "events.jsonl", "metrics.jsonl", "summary.json")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number} must contain a JSON object")
        values.append(value)
    return values


@dataclass(frozen=True)
class RunBundle:
    run_dir: Path
    metadata: dict[str, Any]
    events: tuple[dict[str, Any], ...]
    checkpoints: tuple[dict[str, Any], ...]
    summary: dict[str, Any]
    input_hashes: dict[str, str]

    @property
    def run_id(self) -> str:
        return str(self.metadata.get("run_id") or self.summary.get("run_id") or self.run_dir.name)

    @property
    def condition(self) -> str:
        config = self.metadata.get("config", {})
        return str(config.get("condition", {}).get("memory_mode", self.summary.get("condition", "unknown")))

    @property
    def seed(self) -> int | None:
        config = self.metadata.get("config", {})
        value = config.get("experiment", {}).get("seed", self.summary.get("seed"))
        return int(value) if isinstance(value, int) else None

    @property
    def backend_name(self) -> str:
        backend = self.metadata.get("backend", {})
        return str(backend.get("backend", "unknown")) if isinstance(backend, dict) else str(backend)

    @property
    def is_mock(self) -> bool:
        return self.backend_name == "mock"

    @property
    def agent_ids(self) -> tuple[str, ...]:
        if self.checkpoints:
            values = self.checkpoints[0].get("agent_ids", [])
            if isinstance(values, list):
                return tuple(str(value) for value in values)
        config = self.metadata.get("config", {})
        count = int(config.get("experiment", {}).get("num_agents", 0))
        return tuple(f"agent_{index}" for index in range(count))

    def events_of_type(self, event_type: str) -> list[dict[str, Any]]:
        return [event for event in self.events if event.get("event") == event_type]


def load_run(run_dir: str | Path) -> RunBundle:
    root = Path(run_dir).expanduser().resolve()
    missing = [filename for filename in REQUIRED_RUN_FILES if not (root / filename).is_file()]
    if missing:
        raise FileNotFoundError(f"Run {root} is missing required files: {', '.join(missing)}")
    metadata = _load_json(root / "metadata.json")
    events = _load_jsonl(root / "events.jsonl")
    checkpoints = sorted(_load_jsonl(root / "metrics.jsonl"), key=lambda row: int(row.get("checkpoint", 0)))
    summary = _load_json(root / "summary.json")
    if summary.get("status") != "completed":
        raise ValueError(f"Run {root} is not completed (status={summary.get('status')!r})")
    if not checkpoints:
        raise ValueError(f"Run {root} has no checkpoint metrics")
    hashes = {filename: sha256_file(root / filename) for filename in REQUIRED_RUN_FILES}
    bundle = RunBundle(root, metadata, tuple(events), tuple(checkpoints), summary, hashes)
    run_ids = {str(value) for value in (metadata.get("run_id"), summary.get("run_id")) if value}
    if len(run_ids) > 1:
        raise ValueError(f"Run identifiers disagree in {root}: {sorted(run_ids)}")
    return bundle


def overview_record(bundle: RunBundle) -> dict[str, Any]:
    config = bundle.metadata.get("config", {})
    experiment = config.get("experiment", {})
    agent = config.get("agent", {})
    final = bundle.checkpoints[-1]
    inferences = bundle.events_of_type("inference")
    errors = [event for event in inferences if event.get("error")]
    recorded_usage = usage_summary(bundle)
    return {
        "run_id": bundle.run_id,
        "condition": bundle.condition,
        "seed": bundle.seed,
        "backend": bundle.backend_name,
        "model": agent.get("model", "unknown"),
        "agents": len(bundle.agent_ids),
        "rounds": experiment.get("num_rounds", len(bundle.events_of_type("round_complete"))),
        "checkpoints": len(bundle.checkpoints),
        "probe_count": final.get("probe_count"),
        "inference_attempts": len(inferences),
        "inference_errors": len(errors),
        "final_normalized_hse": final.get("normalized_hse"),
        "final_normalized_mi": final.get("normalized_task_agent_mutual_information"),
        "final_utilization_entropy": final.get("normalized_utilization_entropy"),
        "final_oracle_gain": final.get("oracle_gain"),
        "usage_status": recorded_usage.get("status", "unavailable"),
        "reported_cost": recorded_usage.get("reported_cost"),
        "estimated_cost": recorded_usage.get("estimated_cost"),
    }


def usage_summary(bundle: RunBundle) -> dict[str, Any]:
    """Return run-level usage/cost accounting, recomputed from raw events."""
    config = bundle.metadata.get("config", {})
    cost = config.get("cost", {}) if isinstance(config, dict) else {}
    cost = cost if isinstance(cost, dict) else {}
    events = bundle.events_of_type("inference")
    if not events:
        recorded = bundle.summary.get("usage")
        return recorded if isinstance(recorded, dict) else summarize_usage([])
    return summarize_usage(
        [event.get("token_usage") for event in events],
        currency=str(cost.get("currency", "USD")),
        input_per_million_tokens=cost.get("input_per_million_tokens"),
        cached_input_per_million_tokens=cost.get("cached_input_per_million_tokens"),
        output_per_million_tokens=cost.get("output_per_million_tokens"),
    )


def round_rows(bundle: RunBundle) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in bundle.events_of_type("round_complete"):
        task = event.get("task", {})
        rows.append(
            {
                "run_id": bundle.run_id,
                "condition": bundle.condition,
                "seed": bundle.seed,
                "round": int(event["round"]),
                "world": task.get("world"),
                "x": task.get("x"),
                "y": task.get("y"),
                "selected_agent": event.get("selected_agent_id"),
                "selected_answer": event.get("selected_answer"),
                "correct_answer": event.get("correct_answer"),
                "selected_correct": bool(event.get("selected_correct")),
                "selection_mode": event.get("selection_mode"),
                "tie_size": len(event.get("tied_agent_ids", [])),
                "feedback_recipient_count": len(event.get("feedback_recipients", [])),
            }
        )
    return sorted(rows, key=lambda row: row["round"])


def candidate_rows(bundle: RunBundle) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in bundle.events_of_type("round_complete"):
        task = event.get("task", {})
        selected = event.get("selected_agent_id")
        for agent_id, candidate in event.get("candidates", {}).items():
            rows.append(
                {
                    "run_id": bundle.run_id,
                    "condition": bundle.condition,
                    "seed": bundle.seed,
                    "round": int(event["round"]),
                    "world": task.get("world"),
                    "agent_id": agent_id,
                    "answer": candidate.get("answer"),
                    "confidence": candidate.get("confidence"),
                    "error": candidate.get("error"),
                    "selected": agent_id == selected,
                    "correct": candidate.get("answer") == event.get("correct_answer")
                    if candidate.get("answer") is not None
                    else False,
                }
            )
    return rows


CHECKPOINT_SCALARS = (
    "hse",
    "normalized_hse",
    "task_agent_mutual_information",
    "normalized_task_agent_mutual_information",
    "utilization_entropy",
    "normalized_utilization_entropy",
    "best_individual_accuracy",
    "oracle_society_accuracy",
    "oracle_gain",
    "temporal_role_stability",
)


def checkpoint_rows(bundle: RunBundle) -> list[dict[str, Any]]:
    return [
        {
            "run_id": bundle.run_id,
            "condition": bundle.condition,
            "seed": bundle.seed,
            "checkpoint": int(checkpoint["checkpoint"]),
            **{name: checkpoint.get(name) for name in CHECKPOINT_SCALARS},
        }
        for checkpoint in bundle.checkpoints
    ]


def individual_accuracy_rows(bundle: RunBundle) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for checkpoint in bundle.checkpoints:
        for agent_id, accuracy in zip(checkpoint.get("agent_ids", []), checkpoint.get("individual_accuracy", [])):
            rows.append(
                {
                    "run_id": bundle.run_id,
                    "condition": bundle.condition,
                    "seed": bundle.seed,
                    "checkpoint": int(checkpoint["checkpoint"]),
                    "agent_id": agent_id,
                    "accuracy": accuracy,
                }
            )
    return rows


def competence_rows(bundle: RunBundle) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for checkpoint in bundle.checkpoints:
        for agent_id, worlds in checkpoint.get("competence_matrix", {}).items():
            for world, accuracy in worlds.items():
                rows.append(
                    {
                        "run_id": bundle.run_id,
                        "condition": bundle.condition,
                        "seed": bundle.seed,
                        "checkpoint": int(checkpoint["checkpoint"]),
                        "agent_id": agent_id,
                        "world": world,
                        "accuracy": accuracy,
                    }
                )
    return rows


def routing_rows(bundle: RunBundle) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for checkpoint in bundle.checkpoints:
        for world, agents in checkpoint.get("routing_counts_by_world_agent", {}).items():
            total = sum(int(count) for count in agents.values())
            for agent_id, count in agents.items():
                rows.append(
                    {
                        "run_id": bundle.run_id,
                        "condition": bundle.condition,
                        "seed": bundle.seed,
                        "checkpoint": int(checkpoint["checkpoint"]),
                        "world": world,
                        "agent_id": agent_id,
                        "count": int(count),
                        "proportion": int(count) / total if total else 0.0,
                    }
                )
    return rows


def behavioral_rows(bundle: RunBundle) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for checkpoint in bundle.checkpoints:
        for agent_id, vector in zip(checkpoint.get("agent_ids", []), checkpoint.get("behavioral_matrix", [])):
            for probe_index, success in enumerate(vector):
                rows.append(
                    {
                        "run_id": bundle.run_id,
                        "condition": bundle.condition,
                        "seed": bundle.seed,
                        "checkpoint": int(checkpoint["checkpoint"]),
                        "agent_id": agent_id,
                        "probe_index": probe_index,
                        "success": int(success),
                    }
                )
    return rows


def distance_rows(bundle: RunBundle) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for checkpoint in bundle.checkpoints:
        agent_ids = checkpoint.get("agent_ids", [])
        matrix = checkpoint.get("pairwise_behavioral_cosine_distance", [])
        for left_index, left in enumerate(agent_ids):
            for right_index, right in enumerate(agent_ids):
                rows.append(
                    {
                        "run_id": bundle.run_id,
                        "condition": bundle.condition,
                        "seed": bundle.seed,
                        "checkpoint": int(checkpoint["checkpoint"]),
                        "agent_left": left,
                        "agent_right": right,
                        "distance": matrix[left_index][right_index],
                    }
                )
    return rows


def memory_rows(bundle: RunBundle) -> list[dict[str, Any]]:
    counts = {agent_id: 0 for agent_id in bundle.agent_ids}
    rows = [
        {"run_id": bundle.run_id, "condition": bundle.condition, "seed": bundle.seed, "round": 0, "agent_id": agent_id, "memory_count": 0}
        for agent_id in bundle.agent_ids
    ]
    for event in sorted(bundle.events_of_type("round_complete"), key=lambda row: int(row["round"])):
        for recipient in event.get("feedback_recipients", []):
            counts[recipient] = counts.get(recipient, 0) + 1
        for agent_id in bundle.agent_ids:
            rows.append(
                {
                    "run_id": bundle.run_id,
                    "condition": bundle.condition,
                    "seed": bundle.seed,
                    "round": int(event["round"]),
                    "agent_id": agent_id,
                    "memory_count": counts[agent_id],
                }
            )
    return rows


def inference_rows(bundle: RunBundle) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in bundle.events_of_type("inference"):
        usage = event.get("token_usage") or {}
        normalized = normalize_token_usage(usage if isinstance(usage, dict) else None) or {}
        rows.append(
            {
                "run_id": bundle.run_id,
                "condition": bundle.condition,
                "seed": bundle.seed,
                "phase": event.get("phase"),
                "round": event.get("round_id"),
                "checkpoint": event.get("checkpoint"),
                "probe_index": event.get("probe_index"),
                "agent_id": event.get("agent_id"),
                "attempt": event.get("attempt"),
                "latency_s": event.get("latency_s"),
                "input_tokens": normalized.get("input_tokens"),
                "cached_input_tokens": normalized.get("cached_input_tokens"),
                "output_tokens": normalized.get("output_tokens"),
                "reasoning_tokens": normalized.get("reasoning_tokens"),
                "total_tokens": normalized.get("total_tokens"),
                "error": event.get("error"),
            }
        )
    return rows


def final_metric_rows(bundles: Sequence[RunBundle]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bundle in bundles:
        final = checkpoint_rows(bundle)[-1]
        for metric in (
            "normalized_hse",
            "normalized_task_agent_mutual_information",
            "normalized_utilization_entropy",
            "oracle_gain",
            "oracle_society_accuracy",
            "best_individual_accuracy",
        ):
            rows.append(
                {
                    "run_id": bundle.run_id,
                    "condition": bundle.condition,
                    "seed": bundle.seed,
                    "metric": metric,
                    "value": final.get(metric),
                }
            )
    return rows


def combine_rows(bundles: Iterable[RunBundle], extractor: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bundle in bundles:
        rows.extend(extractor(bundle))
    return rows
