"""Read-only exact GF(7) identifiability audit for calibration JSONL files."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from emergent_specialization.core.environment import HiddenWorldEnvironment
from emergent_specialization.core.gf7 import AffineSolve, evaluate, solve_affine

ROOT = Path(__file__).resolve().parents[3]
PROTOCOLS = ("memory-learnability-v1", "memory-representation-thinking-v1")
DEFAULT_OUTPUT = ROOT / "reports/auto-research/identifiability"


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _events(protocol: str) -> list[dict[str, Any]]:
    path = ROOT / "data/calibrations" / protocol / "events.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _context_key(event: dict[str, Any]) -> str:
    context = event.get("context") or {}
    # The first calibration has a stable context id; the second does not.
    base = str(event.get("context_id") or json.dumps(context, sort_keys=True, separators=(",", ":")))
    # Thinking mode is part of the experimental context, even where the raw
    # context payload itself is otherwise identical.
    return json.dumps({"context": base, "reasoning": event.get("reasoning", "off")}, sort_keys=True, separators=(",", ":"))


def _memory(context: dict[str, Any], kind: str, target_world: str) -> list[dict[str, Any]]:
    """Return only demonstrations from the target world.

    Cross-world calibration contexts deliberately include other worlds.  Those
    rows must not be combined when identifying the target-world affine rule.
    """
    if kind == "truth":
        source = context.get("truth_memory", context.get("memory", []))
    else:
        source = context.get("rendered_memory", context.get("memory", []))
    return [item for item in source if str(item.get("world")) == target_world]


def _solve(memory: list[dict[str, Any]]) -> AffineSolve:
    return solve_affine((int(item["x"]), int(item["y"]), int(item["correct_answer"])) for item in memory)


def _result_columns(prefix: str, result: AffineSolve, probes: list[dict[str, Any]], environment: HiddenWorldEnvironment, world: str) -> dict[str, Any]:
    columns: dict[str, Any] = {f"{prefix}_status": result.status, f"{prefix}_rank": result.rank, f"{prefix}_candidate_count": result.candidate_count}
    coefficients = result.coefficients
    columns[f"{prefix}_coefficients"] = "" if coefficients is None else ",".join(map(str, coefficients))
    columns[f"{prefix}_recovered_environment_rule"] = coefficients == environment_rule(environment, world) if coefficients else False
    if coefficients is None:
        columns[f"{prefix}_symbolic_probe_accuracy"] = ""
    else:
        columns[f"{prefix}_symbolic_probe_accuracy"] = sum(evaluate(coefficients, int(p["x"]), int(p["y"])) == int(p["correct_answer"]) for p in probes) / len(probes) if probes else ""
    return columns


def environment_rule(environment: HiddenWorldEnvironment, world: str) -> tuple[int, int, int]:
    # Recover only by querying the owned environment interface, avoiding a second
    # parallel source of rule constants in this analysis module.
    return (environment.answer_for(world, 1, 0) - environment.answer_for(world, 0, 0)) % 7, (environment.answer_for(world, 0, 1) - environment.answer_for(world, 0, 0)) % 7, environment.answer_for(world, 0, 0)


def generate(output_dir: str | Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    """Audit both immutable calibration event logs and write derived reports only."""
    environment = HiddenWorldEnvironment()
    output = Path(output_dir).resolve()
    rows: list[dict[str, Any]] = []
    for protocol in PROTOCOLS:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for event in _events(protocol):
            if event.get("event") == "completion":
                grouped[_context_key(event)].append(event)
        for context_id, events in sorted(grouped.items()):
            exemplar = events[0]; context = exemplar.get("context") or {}; world = str(exemplar.get("target_world") or context.get("target_world") or context.get("world"))
            if world not in environment.worlds:
                raise ValueError(f"unknown target world in {protocol}: {world!r}")
            probes = [event["probe"] for event in events if event.get("probe")]
            for probe in probes:
                if environment.answer_for(world, int(probe["x"]), int(probe["y"])) != int(probe["correct_answer"]):
                    raise ValueError(f"invalid probe label in {protocol}, context {context_id}")
            all_truth = list(context.get("truth_memory", context.get("memory", [])))
            for item in all_truth:
                item_world = str(item["world"])
                if item_world not in environment.worlds or environment.answer_for(item_world, int(item["x"]), int(item["y"])) != int(item["correct_answer"]):
                    raise ValueError(f"invalid truth-memory label in {protocol}, context {context_id}")
            truth = _memory(context, "truth", world); rendered = _memory(context, "rendered", world)
            successful_events = sum(event.get("error") is None for event in events)
            row = {"protocol": protocol, "context_id": context_id, "reasoning": exemplar.get("reasoning", "off"), "target_world": world, "mode": exemplar.get("mode", context.get("mode")), "representation": exemplar.get("representation", context.get("representation", "")), "k": int(exemplar.get("k", context.get("k", 0))), "context_seed": int(exemplar.get("context_seed", context.get("context_seed", 0))), "physical_events": len(events), "successful_events": successful_events, "error_events": len(events) - successful_events, "has_success": bool(successful_events), "unique_probes": len({str(p.get("task_id", (p["x"], p["y"]))) for p in probes}), "truth_memory_items": len(truth), "rendered_memory_items": len(rendered), "rendered_labels_differ_from_truth": sum(int(a.get("correct_answer")) != int(b.get("correct_answer")) for a, b in zip(truth, rendered))}
            row.update(_result_columns("truth", _solve(truth), probes, environment, world))
            row.update(_result_columns("rendered", _solve(rendered), probes, environment, world))
            rows.append(row)
    _write_csv(output / "context_identifiability.csv", rows)
    summary = {"status": "OFFLINE EXACT GF(7) ANALYSIS ONLY", "protocols": {}, "total_attempted_contexts": len(rows), "notes": {"raw_data": "Read-only JSONL inputs; no network, model, or credential calls.", "truth_memory": "Labels stored as ground-truth exemplars and validated against HiddenWorldEnvironment.", "rendered_memory": "Labels shown to the model; corrupted feedback is intentionally allowed to differ from truth_memory."}}
    for protocol in PROTOCOLS:
        subset = [row for row in rows if row["protocol"] == protocol]
        unique_truth = [r for r in subset if r["truth_status"] == "unique"]
        unique_rendered = [r for r in subset if r["rendered_status"] == "unique"]
        summary["protocols"][protocol] = {"attempted_contexts": len(subset), "contexts_with_success": sum(bool(r["has_success"]) for r in subset), "truth_full_rank_unique_contexts": len(unique_truth), "rendered_full_rank_unique_contexts": len(unique_rendered), "truth_rule_recovery_among_unique": sum(bool(r["truth_recovered_environment_rule"]) for r in unique_truth) / len(unique_truth) if unique_truth else None, "truth_symbolic_probe_accuracy_among_unique": sum(float(r["truth_symbolic_probe_accuracy"]) for r in unique_truth) / len(unique_truth) if unique_truth else None}
    _write_json(output / "identifiability_summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline exact GF(7) hidden-rule identifiability audit")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    print(json.dumps(generate(args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
