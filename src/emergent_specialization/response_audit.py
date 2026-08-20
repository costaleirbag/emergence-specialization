"""Offline audit of response semantics in legacy real-run artifacts."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOTS = {
    "confidence": Path("data/runs/replication"),
    "random": Path("data/runs/campaigns/developmental-dynamics-v1"),
}


def _json_contract(raw: Any) -> tuple[str, int | None, float | None]:
    if not isinstance(raw, str):
        return "none", None, None
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return "malformed", None, None
    if not isinstance(value, dict) or set(value) != {"answer", "confidence"}:
        return "malformed", None, None
    answer = value.get("answer")
    confidence = value.get("confidence")
    if isinstance(answer, bool) or not isinstance(answer, int):
        return "malformed", None, None
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        return "malformed", answer, None
    confidence = float(confidence)
    if not 0.0 <= confidence <= 1.0:
        return "confidence_out_of_domain", answer, confidence
    if not 0 <= answer <= 6:
        return "answer_out_of_domain", answer, confidence
    return "valid", answer, confidence


def _category(event: dict[str, Any]) -> str:
    contract, _, _ = _json_contract(event.get("raw_model_response"))
    if contract == "answer_out_of_domain":
        return "semantic_answer_domain_violation"
    if contract == "confidence_out_of_domain":
        return "confidence_domain_violation"
    if event.get("error_category") in {"timeout", "transient_transport", "rate_limit", "server_error", "overloaded", "empty_content"}:
        return "transport_provider_failure"
    if event.get("error_category") == "parse_error" or contract == "malformed":
        return "malformed_unreadable_output"
    if event.get("error"):
        return "other"
    return "valid"


def audit_runs() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for router, root in ROOTS.items():
        if not root.exists():
            continue
        for event_path in sorted(root.glob("*/events.jsonl")):
            try:
                metadata = json.loads((event_path.parent / "metadata.json").read_text(encoding="utf-8"))
                config = metadata.get("config", {})
                actual_router = config.get("router", {}).get("strategy", router)
                condition = config.get("condition", {}).get("memory_mode")
                seed = config.get("experiment", {}).get("seed")
                events = [json.loads(line) for line in event_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
                continue
            selected_by_round = {
                (event.get("round")): event.get("selected_agent_id")
                for event in events
                if event.get("event") == "round_complete"
            }
            by_logical: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for event in events:
                if event.get("event") == "inference":
                    by_logical[str(event.get("logical_id"))].append(event)
            for event in events:
                if event.get("event") != "inference":
                    continue
                category = _category(event)
                if category == "valid":
                    continue
                logical = by_logical.get(str(event.get("logical_id")), [event])
                eventual_success = any(item.get("error") is None for item in logical)
                selected = (
                    event.get("phase") == "round"
                    and selected_by_round.get(event.get("round_id")) == event.get("agent_id")
                )
                rows.append({
                    "run_id": event.get("run_id"),
                    "router": actual_router,
                    "condition": condition,
                    "seed": seed,
                    "phase": event.get("phase"),
                    "round_id": event.get("round_id"),
                    "checkpoint": event.get("checkpoint"),
                    "probe_index": event.get("probe_index"),
                    "agent_id": event.get("agent_id"),
                    "attempt": event.get("attempt"),
                    "first_attempt": int(event.get("attempt", 0)) == 0,
                    "category": category,
                    "event_error_category": event.get("error_category"),
                    "event_error": event.get("error"),
                    "eventual_retry_success": eventual_success,
                    "selected_interaction_candidate": selected,
                    "raw_model_response": event.get("raw_model_response"),
                })
    return rows


def _csv(path: Path, rows: list[dict[str, Any]]) -> None:
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row}) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def generate_reports(*, audit_rows: list[dict[str, Any]] | None = None) -> tuple[Path, Path, list[dict[str, Any]]]:
    rows = audit_rows if audit_rows is not None else audit_runs()
    docs = Path("docs")
    docs.mkdir(parents=True, exist_ok=True)
    _csv(docs / "response_semantics_audit.csv", rows)

    def section(title: str, subset: list[dict[str, Any]]) -> list[str]:
        counts = Counter(row["category"] for row in subset)
        phases = Counter(row["phase"] for row in subset)
        conditions = Counter(row["condition"] for row in subset)
        routers = Counter(row["router"] for row in subset)
        return [
            f"### {title}",
            "",
            f"- count: **{len(subset)}**",
            f"- by phase: `{dict(phases)}`",
            f"- by condition: `{dict(conditions)}`",
            f"- by router: `{dict(routers)}`",
            f"- first attempts: **{sum(bool(row['first_attempt']) for row in subset)}**",
            f"- events whose logical completion eventually succeeded via old retry: **{sum(bool(row['eventual_retry_success']) for row in subset)}**",
            f"- selected interaction candidates: **{sum(bool(row['selected_interaction_candidate']) for row in subset)}**",
            "",
        ]

    lines = [
        "# Response semantics audit",
        "",
        "> Offline audit of legacy real-run inference events. This document does not modify raw artifacts and makes no new model calls.",
        "",
        "## Classification",
        "",
        "The audit distinguishes transport/provider failures, malformed/unreadable output, semantic answer-domain violations, confidence-domain violations and other errors. A valid JSON object with an integer answer outside `[0,6]` and confidence inside `[0,1]` is classified as a scientific answer-domain violation, even though legacy runs logged it as a parse error.",
        "",
    ]
    for category, title in (
        ("transport_provider_failure", "A. Transport/provider failures"),
        ("malformed_unreadable_output", "B. Malformed/unreadable model output"),
        ("semantic_answer_domain_violation", "C. Semantic answer-domain violations"),
        ("confidence_domain_violation", "D. Confidence-domain violations"),
        ("other", "E. Other"),
    ):
        lines.extend(section(title, [row for row in rows if row["category"] == category]))
    lines += [
        "## Key consequence",
        "",
        "The old parser treated answer-domain violations as retryable technical failures. Probe-only cases affect measurement but can be sensitivity-scored offline. Interaction cases can change the selected candidate, stored `Experience.prediction`, memory state and all later trajectory; they cannot be exactly repaired offline. Therefore the old Gate 1 and random-v1 artifacts remain LEGACY / EXPLORATORY evidence.",
        "",
        "The complete event-level table is `docs/response_semantics_audit.csv`; raw run directories remain unchanged.",
    ]
    audit_path = docs / "RESPONSE_SEMANTICS_AUDIT.md"
    audit_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    gate1 = [row for row in rows if row["router"] == "confidence"]
    random = [row for row in rows if row["router"] == "random"]
    def impact_doc(title: str, subset: list[dict[str, Any]], note: str) -> Path:
        counts = Counter(row["category"] for row in subset)
        interaction = [row for row in subset if row["phase"] == "round" and row["category"] == "semantic_answer_domain_violation"]
        probes = [row for row in subset if row["phase"] == "probe" and row["category"] == "semantic_answer_domain_violation"]
        text = [
            f"# {title}",
            "",
            "> LEGACY / EXPLORATORY impact analysis. Raw artifacts are immutable; this is an offline sensitivity audit.",
            "",
            f"- Semantic answer-domain events: **{counts['semantic_answer_domain_violation']}**",
            f"- Interaction semantic events: **{len(interaction)}**",
            f"- Probe semantic events: **{len(probes)}**",
            f"- Interaction events that were selected candidates under the old retry-resolved trajectory: **{sum(bool(row['selected_interaction_candidate']) for row in interaction)}**",
            f"- Semantic events whose old logical completion eventually succeeded on retry: **{sum(bool(row['eventual_retry_success']) for row in subset if row['category'] == 'semantic_answer_domain_violation')}**",
            "",
            note,
            "",
            "The event-level details are in `docs/response_semantics_audit.csv`. Probe-only cases can be scored as incorrect without replaying the model. Interaction cases cannot be exactly reconstructed because the old retry response may have changed memory and routing.",
        ]
        path = docs / ("GATE1_SEMANTIC_RETRY_IMPACT.md" if title.startswith("Gate 1") else "RANDOM_V1_SEMANTIC_RETRY_IMPACT.md")
        path.write_text("\n".join(text) + "\n", encoding="utf-8")
        return path

    gate1_path = impact_doc(
        "Gate 1 semantic-retry impact",
        gate1,
        "Gate 1's original 10 paired seeds are complete under legacy retry semantics, but interaction out-of-domain first attempts occurred in at least private seed 8 round 2 and private seed 9 round 14. The old Gate 1 remains useful exploratory history, not clean confirmatory evidence.",
    )
    random_path = impact_doc(
        "Random-v1 semantic-retry impact",
        random,
        "Random-v1 seeds 1–2 completed under legacy retry semantics; private seed 3 is invalid/incomplete. Its interaction seed-3 round-10 out-of-domain first attempt was retried and the retry response became the selected candidate, so this artifact must not be mixed with the corrected protocol.",
    )
    return audit_path, gate1_path, rows


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Audit legacy response semantics offline")
    parser.parse_args(list(argv) if argv is not None else None)
    paths = generate_reports()
    print(paths[0])
    print(paths[1])


if __name__ == "__main__":
    main()
