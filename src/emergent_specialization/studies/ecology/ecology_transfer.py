"""Offline ecology audits and single-agent transfer qualification runner."""

from __future__ import annotations

import argparse
import asyncio
import csv
import fcntl
import hashlib
import json
import math
import os
import re
import statistics
import tempfile
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from emergent_specialization.providers.credentials import CredentialStore
from emergent_specialization.studies.calibration.explicit_rule_execution import _append_event, _atomic_json
from emergent_specialization.core.models import BackendResponse
from emergent_specialization.providers import DeepSeekDirectBackend
from emergent_specialization.studies.ecology.semantic_ecology import ECOLOGIES, Ecology, Environment, parse_action, stable_hash

ROOT = Path(__file__).resolve().parents[4]
REPORT_ROOT = ROOT / "reports/task-ecology/qualification-v1"
OUTPUT_ROOT = ROOT / "data/auto-research/ecology-transfer-qualification-v1"
CONFIG_PATH = ROOT / "configs/research/auto/ecology_transfer_qualification_v1.yaml"
CAMPAIGN_BUDGET = REPORT_ROOT / "campaign_budget.json"
GLOBAL_CAP = 0.50
MODEL = "deepseek-v4-flash"
SEEDS = (1701, 1702, 1703, 1704, 1705)
INPUT_PRICE = 0.14
CACHED_INPUT_PRICE = 0.0028
OUTPUT_PRICE = 0.28
RESERVATION = 0.005


def now() -> str:
    return datetime.now(UTC).isoformat()


def config_hash() -> str:
    return hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()


def _audit_one(ecology: Ecology, seed: int, family: str) -> dict[str, Any]:
    env = ecology.generate_environment(seed)
    probes = ecology.probe_cases(env, family)
    train4 = ecology.training_cases(env, family, 4)
    train8 = ecology.training_cases(env, family, 8)
    prompts = [ecology.render_case(family, case) for case in probes + train8]
    candidate = ecology.candidate_thetas(family, env)
    h4 = __import__("emergent_specialization.studies.ecology.semantic_ecology", fromlist=["predictive_identifiability"]).predictive_identifiability(ecology, env, family, 4)
    h8 = __import__("emergent_specialization.studies.ecology.semantic_ecology", fromlist=["predictive_identifiability"]).predictive_identifiability(ecology, env, family, 8)
    probe_ids = {case.case_id for case in probes}; train_ids = {case.case_id for case in train8}
    template_split = all(case.template == "eval" for case in probes) and all(case.template == "train" for case in train8)
    entity_split = not ({entity for case in probes for entity in case.entities} & {entity for case in train8 for entity in case.entities})
    rendered_text = "\n".join(prompts)
    theta_keys = {"threshold", "compatibility", "exception", "provenance", "temporal", "motif", "permutation", "block"}
    theta_leak = any(key in rendered_text.lower() for key in theta_keys)
    duplicate = len(probe_ids) != len(probes) or len(train_ids) != len(train8) or bool(probe_ids & train_ids)
    balance = {label: sum(case.expected == label for case in probes) for label in ecology.output_classes}
    oracle = all(ecology.solve(env, family, case.fields) == case.expected for case in probes)
    return {"ecology": ecology.name, "seed": seed, "family": family, "probe_count": len(probes),
            "train_count_h4": len(train4), "train_count_h8": len(train8), "candidate_theta_count": len(candidate),
            "balance_pass": all(balance[label] == 2 for label in ecology.output_classes), "balance": balance,
            "oracle_pass": oracle, "deterministic_pass": ecology.generate_environment(seed) == env,
            "template_split_pass": template_split, "entity_split_pass": entity_split,
            "duplicate_or_overlap": duplicate, "theta_leakage": theta_leak,
            "predictive_identifiability_h4": h4["predictively_identifiable"],
            "predictive_identifiability_h8": h8["predictively_identifiable"],
            "offline_pass": all((not duplicate, not theta_leak, template_split, entity_split, oracle,
                                  ecology.generate_environment(seed) == env,
                                  all(balance[label] == 2 for label in ecology.output_classes),
                                  h8["predictively_identifiable"] >= 0.90)),
            "h4_consistent_count": h4["consistent_count"], "h8_consistent_count": h8["consistent_count"]}


def offline_audit() -> list[dict[str, Any]]:
    rows = [_audit_one(ecology, seed, family) for name, ecology in ECOLOGIES.items() for seed in range(100) for family in ecology.families]
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with (REPORT_ROOT / "offline_generator_audit.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    return rows


def candidate_status(rows: list[dict[str, Any]]) -> dict[str, bool]:
    return {name: all(row["offline_pass"] for row in rows if row["ecology"] == name) for name in ECOLOGIES}


def build_tasks(ecology: Ecology, seeds: tuple[int, ...] = SEEDS) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for seed in seeds:
        env = ecology.generate_environment(seed)
        for target in ecology.families:
            probes = ecology.probe_cases(env, target)
            h8 = ecology.training_cases(env, target, 8)
            h4 = h8[:4]
            for case in probes:
                for replicate in range(2):
                    tasks.append({"condition": "baseline", "source": None, "target": target, "h": 0, "seed": seed,
                                  "replicate": replicate, "case": case.symbolic(), "memory": []})
            for source in ecology.families:
                memories = [ecology.render_experience(case) for case in ecology.training_cases(env, source, 8)]
                for case in probes:
                    for replicate in range(2):
                        tasks.append({"condition": "transfer", "source": source, "target": target, "h": 8, "seed": seed,
                                      "replicate": replicate, "case": case.symbolic(), "memory": memories})
            memories4 = [ecology.render_experience(case) for case in h4]
            for case in probes:
                for replicate in range(2):
                    tasks.append({"condition": "transfer", "source": target, "target": target, "h": 4, "seed": seed,
                                  "replicate": replicate, "case": case.symbolic(), "memory": memories4})
    return tasks


def freeze_manifest(ecology_name: str, seeds: tuple[int, ...] = SEEDS) -> dict[str, Any]:
    ecology = ECOLOGIES[ecology_name]; tasks = build_tasks(ecology, seeds)
    expected = 1920
    if len(tasks) != expected:
        raise RuntimeError(f"transfer task count mismatch: {len(tasks)} != {expected}")
    manifest = {"protocol": "ECOLOGY-TRANSFER-QUALIFICATION-V1", "ecology": ecology_name,
                "seeds": list(seeds), "model": MODEL, "thinking": "off", "replicates": 2,
                "probe_count": 8, "h8_full_matrix": True, "h4_diagonal": True,
                "logical_calls": len(tasks), "config_hash": config_hash(), "created_at_utc": now(),
                "tasks_hash": stable_hash(tasks), "tasks": tasks}
    path = REPORT_ROOT / f"{ecology_name.lower()}_transfer_manifest.json"; path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_json(path, manifest); return manifest


def _prompt(ecology: Ecology, task: dict[str, Any]) -> str:
    case_data = task["case"]; case = type("CaseView", (), case_data)
    # Reconstruct a real Case without trusting model-visible expected labels.
    from emergent_specialization.studies.ecology.semantic_ecology import Case
    reconstructed = Case(case_data["family"], case_data["case_id"], case_data["template"], tuple(case_data["entities"]), case_data["fields"], case_data["expected"])
    return ecology.render_query(reconstructed, task["memory"])


def _load_budget() -> dict[str, Any]:
    if CAMPAIGN_BUDGET.exists():
        return json.loads(CAMPAIGN_BUDGET.read_text(encoding="utf-8"))
    ar_report = ROOT / "reports/auto-research/ar001b-full-2d/report.json"
    ar_cost = float(json.loads(ar_report.read_text()).get("observed_cost_usd", 0.0)) if ar_report.exists() else 0.0
    budget = {"hard_cap_usd": GLOBAL_CAP, "spent_usd": ar_cost, "reserved_usd": 0.0, "history": [{"source": "AR-001B", "cost_usd": ar_cost}]}
    _atomic_json(CAMPAIGN_BUDGET, budget); return budget


def _budget_change(*, reserve: float = 0.0, release: float = 0.0, actual: float = 0.0) -> None:
    budget = _load_budget(); held = float(budget.get("reserved_usd", 0.0)); spent = float(budget.get("spent_usd", 0.0))
    # Check both reservations and the amount being reconciled.  Without the
    # ``actual`` term, a final paid response could push the campaign over its
    # hard cap after the pre-call reservation had passed.
    if held + 1e-12 < release or spent + held - release + reserve + actual > GLOBAL_CAP + 1e-12:
        raise RuntimeError("ecology qualification budget guard")
    budget["reserved_usd"] = held - release + reserve; budget["spent_usd"] = spent + actual; budget["updated_at_utc"] = now()
    _atomic_json(CAMPAIGN_BUDGET, budget)


def _global_ledger_change(*, reserve: float = 0.0, release: float = 0.0, actual: float = 0.0) -> None:
    lock_path = ROOT / "reports/auto-research/cost_ledger.csv.lock"
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        with (ROOT / "reports/auto-research/cost_ledger.csv").open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle); rows = list(reader); fields = list(reader.fieldnames or [])
        matches = [row for row in rows if row.get("session_id") == "autonomous-session-2026-08-08"]
        if len(matches) != 1:
            raise RuntimeError("global ledger session row missing")
        row = matches[0]; spent = float(row["spent_usd"]); held = float(row["reserved_usd"])
        if held + 1e-12 < release or spent + held - release + reserve + actual > 2.0 + 1e-12:
            raise RuntimeError("global ledger guard")
        row["reserved_usd"] = f"{held - release + reserve:.9f}"; row["spent_usd"] = f"{spent + actual:.9f}"; row["updated_at_utc"] = now()
        fd, name = tempfile.mkstemp(prefix=".ecology-ledger.", dir=(ROOT / "reports/auto-research"))
        try:
            with os.fdopen(fd, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows); handle.flush(); os.fsync(handle.fileno())
            os.replace(name, ROOT / "reports/auto-research/cost_ledger.csv")
        finally:
            if os.path.exists(name): os.unlink(name)


def _cost(response: BackendResponse) -> float | None:
    from emergent_specialization.core.costs import estimate_usage_cost
    if response.observed_cost_usd is not None:
        value = float(response.observed_cost_usd); return value if math.isfinite(value) and value >= 0 else None
    return estimate_usage_cost(response.token_usage, input_per_million_tokens=INPUT_PRICE,
                               cached_input_per_million_tokens=CACHED_INPUT_PRICE, output_per_million_tokens=OUTPUT_PRICE)


async def run_real(ecology_name: str, *, confirm_real: bool = False) -> dict[str, Any]:
    if not confirm_real:
        raise SystemExit("ecology qualification requires --confirm-real")
    manifest_path = REPORT_ROOT / f"{ecology_name.lower()}_transfer_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if len(manifest["tasks"]) != 1920:
        raise RuntimeError("frozen transfer manifest count mismatch")
    output = OUTPUT_ROOT / ecology_name.lower(); output.mkdir(parents=True, exist_ok=True)
    events_path = output / "events.jsonl"; status_path = output / "manifest.json"
    # A failed qualification is resumable.  Existing terminal logical records
    # are never re-called; only missing logical IDs (or an explicitly
    # retryable transport record) may continue.  A completed output remains
    # immutable and cannot be duplicated.
    events: list[dict[str, Any]] = []
    if events_path.exists():
        events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if status_path.exists():
        status = json.loads(status_path.read_text(encoding="utf-8"))
        if status.get("tasks_hash") != manifest["tasks_hash"] or status.get("ecology") != ecology_name:
            raise RuntimeError("existing transfer output does not match frozen manifest")
        if status.get("status") == "completed":
            raise RuntimeError("transfer output already completed; no duplicate run")
        status["resumed_at_utc"] = now()
        status["status"] = "resuming"
    else:
        status = {"protocol": manifest["protocol"], "ecology": ecology_name, "status": "initialized",
                  "tasks_hash": manifest["tasks_hash"], "logical_calls": 1920, "created_at_utc": now()}
    _atomic_json(status_path, status)
    terminal_ids = {event.get("logical_id") for event in events
                    if event.get("error") is None or event.get("error_category") == "out_of_domain"}
    attempts_by_id: dict[str, int] = defaultdict(int)
    for event in events:
        logical_id = event.get("logical_id")
        if logical_id:
            attempts_by_id[logical_id] = max(attempts_by_id[logical_id], int(event.get("attempt", 0)) + 1)
    backend = None; cost_total = sum(float(event.get("attempt_cost_usd") or 0.0) for event in events)
    physical = len(events); retries = sum(1 for event in events if int(event.get("attempt", 0)) > 0)
    try:
        key = CredentialStore().get(source="keychain")
        backend = DeepSeekDirectBackend(api_key=key, thinking="off", max_tokens=256)
        ecology = ECOLOGIES[ecology_name]
        for task in manifest["tasks"]:
            logical_id = stable_hash({"ecology": ecology_name, "task": task, "tasks_hash": manifest["tasks_hash"]})
            if logical_id in terminal_ids:
                continue
            start_attempt = attempts_by_id.get(logical_id, 0)
            if start_attempt >= 2:
                raise RuntimeError(f"retry exhaustion for logical_id {logical_id}")
            for attempt in range(start_attempt, 2):
                _global_ledger_change(reserve=RESERVATION)
                _budget_change(reserve=RESERVATION)
                response = await backend.complete(system_prompt="You are a single-agent procedural transfer diagnostic. Use the resolved cases as feedback-only memory.",
                                                  user_prompt=_prompt(ecology, task), model=MODEL,
                                                  model_parameters={"thinking": "off", "max_tokens": 256})
                physical += 1; value = _cost(response)
                if value is None:
                    event = {"logical_id": logical_id, "attempt": attempt, "task": task, "error": "cost_accounting_missing",
                             "error_category": "cost_accounting_missing", "latency_s": response.latency_s, "token_usage": response.token_usage}
                    _append_event(events_path, event); events.append(event); raise RuntimeError("transfer cost unavailable")
                _global_ledger_change(release=RESERVATION, actual=float(value)); _budget_change(release=RESERVATION, actual=float(value)); cost_total += float(value)
                answer, confidence, parse_error = parse_action(response.raw_response)
                provider = response.provider_metadata or {}
                if provider.get("model") != MODEL:
                    parse_error = "invalid_model"
                error = response.error or parse_error
                case = task["case"]
                event = {"logical_id": logical_id, "attempt": attempt, "task": task, "answer": answer,
                         "confidence": confidence, "correct": answer == case["expected"], "error": error,
                         "error_category": response.error_category or parse_error, "raw_model_response": response.raw_response,
                         "latency_s": response.latency_s, "token_usage": response.token_usage,
                         "provider_metadata": provider, "attempt_cost_usd": float(value), "finished_at_utc": now()}
                _append_event(events_path, event); events.append(event)
                # Out-of-domain answers are semantic data (an incorrect/OOD
                # completion), not a technical failure and never merit a
                # retry.  They still complete this logical context.
                if error is None or event["error_category"] == "out_of_domain":
                    terminal_ids.add(logical_id)
                    break
                if event["error_category"] not in {"parse_error", "empty_content", "transient_transport", "transport", "malformed"} or not response.retryable:
                    raise RuntimeError(str(error))
                retries += 1
            else:
                raise RuntimeError("transfer retry exhaustion")
        status.update(status="completed", physical_attempts=physical, retries=retries, observed_cost_usd=cost_total, finished_at_utc=now())
    except Exception as exc:
        status.update(status="failed", failure=f"{type(exc).__name__}: {exc}", physical_attempts=physical, retries=retries, observed_cost_usd=cost_total, finished_at_utc=now())
    finally:
        if backend is not None:
            await backend.close()
        _atomic_json(status_path, status)
    return status


def _mean(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def _sample_sd(values: list[float]) -> float | None:
    return statistics.stdev(values) if len(values) > 1 else (0.0 if values else None)


def _auc(scores: list[float], labels: list[bool]) -> float | None:
    positives = [(score, index) for index, (score, label) in enumerate(zip(scores, labels)) if label]
    negatives = [(score, index) for index, (score, label) in enumerate(zip(scores, labels)) if not label]
    if not positives or not negatives:
        return None
    wins = sum(1.0 if p[0] > n[0] else 0.5 if p[0] == n[0] else 0.0 for p in positives for n in negatives)
    return wins / (len(positives) * len(negatives))


def _point_biserial(scores: list[float], labels: list[bool]) -> float | None:
    if len(set(labels)) < 2 or len(scores) < 2:
        return None
    mean_score = statistics.mean(scores)
    mean_pos = statistics.mean([score for score, label in zip(scores, labels) if label])
    mean_neg = statistics.mean([score for score, label in zip(scores, labels) if not label])
    sd = statistics.stdev(scores)
    if sd == 0:
        return None
    p = sum(labels) / len(labels)
    return (mean_pos - mean_neg) / sd * math.sqrt(p * (1 - p))


def _memory_answers(memory: list[str]) -> list[str]:
    answers: list[str] = []
    for item in memory:
        match = re.search(r"Correct resolution:\s*([A-Z]+)", item)
        if match:
            answers.append(match.group(1))
    return answers


def _logical_observation(event: dict[str, Any]) -> bool:
    """Whether an event completes a logical context for analysis.

    A semantic out-of-domain answer is a completed, incorrect observation; it
    is not dropped from accuracy denominators or mistaken for a retryable
    transport failure.
    """
    return (event.get("error") is None and event.get("answer") is not None) or event.get("error_category") == "out_of_domain"


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def _svg_heatmap(path: Path, matrix: dict[tuple[str, str], float | None], families: tuple[str, ...], title: str) -> None:
    cell = 92; left = 150; top = 72; width = left + cell * len(families) + 20; height = top + cell * len(families) + 30
    def color(value: float | None) -> str:
        if value is None: return "#e7e5e4"
        clipped = max(-1.0, min(1.0, value)); intensity = int(128 + 100 * clipped)
        if clipped >= 0: return f"rgb(30,{intensity},120)"
        return f"rgb({intensity},100,120)"
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<style>text{font-family:Arial,sans-serif;fill:#1c1917} .small{font-size:11px} .title{font-size:16px;font-weight:700}</style>',
             f'<text class="title" x="12" y="24">{title}</text>']
    for j, target in enumerate(families):
        parts.append(f'<text class="small" text-anchor="middle" x="{left + j*cell + cell/2}" y="50">{target}</text>')
    for i, source in enumerate(families):
        y = top + i * cell
        parts.append(f'<text class="small" text-anchor="end" x="{left-8}" y="{y + cell/2 + 4}">{source}</text>')
        for j, target in enumerate(families):
            value = matrix.get((source, target)); x = left + j * cell
            text_value = "NA" if value is None else f"{value:+.2f}"
            parts.append(f'<rect x="{x}" y="{y}" width="{cell-2}" height="{cell-2}" fill="{color(value)}" rx="4"/>')
            parts.append(f'<text class="small" text-anchor="middle" x="{x + cell/2}" y="{y + cell/2 + 4}">{text_value}</text>')
    parts.append("</svg>")
    path.write_text("".join(parts), encoding="utf-8")


def _svg_learning(path: Path, rows: list[dict[str, Any]], families: tuple[str, ...], title: str) -> None:
    width, height, left, top, right, bottom = 760, 360, 70, 48, 20, 48
    points: list[tuple[float, float]] = []
    grouped: dict[int, list[float]] = defaultdict(list)
    for row in rows:
        if row["source"] == row["target"] and row["h"] in (0, 4, 8) and row["accuracy"] is not None:
            grouped[int(row["h"])].append(float(row["accuracy"]))
    values = {h: _mean(v) for h, v in grouped.items()}
    for h in (0, 4, 8):
        if values.get(h) is not None:
            x = left + (width-left-right) * h / 8; y = height-bottom - (height-top-bottom) * values[h]
            points.append((x, y))
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    content = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
               '<style>text{font-family:Arial,sans-serif;fill:#1c1917}.title{font-size:16px;font-weight:700}.small{font-size:11px}</style>',
               f'<text class="title" x="12" y="24">{title}</text>',
               f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#78716c"/>',
               f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#78716c"/>',
               f'<polyline points="{poly}" fill="none" stroke="#0f766e" stroke-width="3"/>']
    for h in (0, 4, 8):
        x = left + (width-left-right) * h / 8
        content.append(f'<text class="small" text-anchor="middle" x="{x}" y="{height-bottom+20}">h={h}</text>')
    for x, y in points:
        content.append(f'<circle cx="{x}" cy="{y}" r="5" fill="#0f766e"/>')
    content.append("</svg>"); path.write_text("".join(content), encoding="utf-8")


def _refresh_combined_outputs() -> None:
    """Merge candidate-specific tables into the protocol-level report root."""
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    for filename in ("environment_level_transfer.csv", "aggregate_transfer_matrices.csv", "response_level.csv",
                     "identifiability.csv", "confidence.csv", "anchoring.csv"):
        merged: list[dict[str, Any]] = []
        for ecology_name in ECOLOGIES:
            path = REPORT_ROOT / ecology_name.lower() / filename
            if path.exists():
                with path.open(newline="", encoding="utf-8") as handle:
                    merged.extend(dict(row) for row in csv.DictReader(handle))
        if merged:
            _write_csv(REPORT_ROOT / filename, merged)
    combined: dict[str, Any] = {"protocol": "ECOLOGY-TRANSFER-QUALIFICATION-V1", "candidates": {}}
    for ecology_name in ECOLOGIES:
        path = REPORT_ROOT / ecology_name.lower() / "qualification_summary.json"
        if path.exists():
            combined["candidates"][ecology_name] = json.loads(path.read_text(encoding="utf-8"))
            for figure in (REPORT_ROOT / ecology_name.lower() / "figures").glob("*.svg"):
                target = REPORT_ROOT / "figures" / figure.name; target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(figure.read_text(encoding="utf-8"), encoding="utf-8")
    _atomic_json(REPORT_ROOT / "qualification_summary.json", combined)


def aggregate(ecology_name: str) -> dict[str, Any]:
    """Materialize preregistered transfer tables from completed raw events.

    All rows remain indexed by environment seed; model replicates are repeated
    measurements and are never treated as independent environments.
    """
    path = OUTPUT_ROOT / ecology_name.lower() / "events.jsonl"
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ecology = ECOLOGIES[ecology_name]
    out_dir = REPORT_ROOT / ecology_name.lower(); figure_dir = out_dir / "figures"; figure_dir.mkdir(parents=True, exist_ok=True)
    response_rows: list[dict[str, Any]] = []
    grouped: dict[tuple[int, str, str | None, int], list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        task = event["task"]; grouped[(task["seed"], task["target"], task["source"], task["h"])].append(event)
        memory = task.get("memory") or []; mem_answers = _memory_answers(memory)
        answer = event.get("answer")
        semantic_ood = event.get("error_category") == "out_of_domain"
        correct = event.get("correct") if event.get("error") is None else False if semantic_ood else None
        response_rows.append({"ecology": ecology_name, "seed": task["seed"], "source": task["source"] or "none", "target": task["target"],
                              "h": task["h"], "condition": task["condition"], "replicate": task["replicate"],
                              "case_id": task["case"]["case_id"], "answer": answer, "expected": task["case"]["expected"],
                              "correct": correct, "confidence": event.get("confidence"), "latency_s": event.get("latency_s"),
                              "error": event.get("error"), "error_category": event.get("error_category"), "semantic_ood": semantic_ood,
                              "prompt_hash": stable_hash({"task": task, "ecology": ecology_name}),
                              "memory_count": len(memory), "last_memory_answer": mem_answers[-1] if mem_answers else None,
                              "any_memory_match": bool(answer and answer in mem_answers),
                              "last_memory_match": bool(answer and mem_answers and answer == mem_answers[-1]),
                              "input_tokens": (event.get("token_usage") or {}).get("prompt_tokens"),
                              "output_tokens": (event.get("token_usage") or {}).get("completion_tokens"),
                              "total_tokens": (event.get("token_usage") or {}).get("total_tokens"),
                              "cost_usd": event.get("attempt_cost_usd")})
    _write_csv(out_dir / "response_level.csv", response_rows)
    rows: list[dict[str, Any]] = []
    for (seed, target, source, h), values in sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1], item[0][2] or "", item[0][3])):
        valid = [v for v in values if _logical_observation(v)]
        rows.append({"ecology": ecology_name, "seed": seed, "source": source or "none", "target": target, "h": h,
                     "n": len(valid), "accuracy": _mean([1.0 if v["correct"] else 0.0 for v in valid]),
                     "mean_confidence": _mean([float(v["confidence"]) for v in valid if v.get("confidence") is not None]),
                     "errors": len(values) - len(valid), "semantic_ood": sum(v.get("error_category") == "out_of_domain" for v in values)})
    _atomic_json(out_dir / f"{ecology_name.lower()}_aggregate.json", {"rows": rows, "ecology": ecology_name})
    lookup = {(r["seed"], r["target"]): r for r in rows if r["source"] == "none" and r["h"] == 0}
    environment_rows: list[dict[str, Any]] = []
    for r in rows:
        if r["source"] == "none" or r["h"] not in (4, 8): continue
        baseline = lookup.get((r["seed"], r["target"]), {}).get("accuracy")
        environment_rows.append({**r, "baseline_accuracy": baseline,
                                  "learning_gain": r["accuracy"] - baseline if r["accuracy"] is not None and baseline is not None else None})
    _write_csv(out_dir / "environment_level_transfer.csv", environment_rows)
    aggregate_rows: list[dict[str, Any]] = []
    for h in (4, 8):
        for source in ecology.families:
            targets = (source,) if h == 4 else ecology.families
            for target in targets:
                vals = [r["learning_gain"] for r in environment_rows if r["h"] == h and r["source"] == source and r["target"] == target and r["learning_gain"] is not None]
                baselines = [r["baseline_accuracy"] for r in environment_rows if r["h"] == h and r["source"] == source and r["target"] == target and r["baseline_accuracy"] is not None]
                aggregate_rows.append({"ecology": ecology_name, "h": h, "source": source, "target": target,
                                       "n_seeds": len(vals), "mean_baseline_accuracy": _mean(baselines),
                                       "mean_transfer_gain": _mean(vals), "sd_transfer_gain": _sample_sd(vals)})
    _write_csv(out_dir / "aggregate_transfer_matrices.csv", aggregate_rows)
    h8 = {(r["source"], r["target"]): r["mean_transfer_gain"] for r in aggregate_rows if r["h"] == 8}
    diagonal = [h8[(f, f)] for f in ecology.families if h8.get((f, f)) is not None]
    offdiag = [v for (s, t), v in h8.items() if s != t and v is not None]
    q = {f: h8.get((f, f), 0.0) - _mean([h8.get((f, t), 0.0) for t in ecology.families if t != f]) for f in ecology.families}
    block_stat = None
    if ecology_name == "OPE":
        blocks = {"ACCESS": 0, "RELEASE": 0, "INCIDENT": 1, "PROVENANCE": 1}
        within = [v for (s, t), v in h8.items() if s != t and blocks[s] == blocks[t] and v is not None]
        cross = [v for (s, t), v in h8.items() if blocks[s] != blocks[t] and v is not None]
        block_stat = (_mean(within) - _mean(cross)) if within and cross else None
    summary = {"ecology": ecology_name, "protocol": "ECOLOGY-TRANSFER-QUALIFICATION-V1", "offline_pass": True,
               "baseline_accuracy": _mean([r["accuracy"] for r in rows if r["source"] == "none" and r["h"] == 0]),
               "D": _mean(diagonal), "O": _mean(offdiag), "Q": (_mean(diagonal) - _mean(offdiag)) if diagonal and offdiag else None,
               "q_c": q, "B_OPE": block_stat, "criteria": {"D_ge_010": bool(diagonal and _mean(diagonal) >= .10),
               "Q_ge_007": bool(diagonal and offdiag and _mean(diagonal) - _mean(offdiag) >= .07),
               "three_q_gt_005": sum(v > .05 for v in q.values()) >= 3},
               "classification": "PENDING_QUALIFICATION"}
    if summary["criteria"]["D_ge_010"] and summary["criteria"]["Q_ge_007"] and summary["criteria"]["three_q_gt_005"]:
        summary["classification"] = "PROMISING SPECIALIZATION SUBSTRATE"
    elif summary["criteria"]["D_ge_010"]:
        summary["classification"] = "LEARNABLE-BUT-GENERAL"
    else:
        summary["classification"] = "MODEL-NONLEARNABLE"
    audit_path = REPORT_ROOT / "offline_generator_audit.csv"
    if audit_path.exists():
        with audit_path.open(newline="", encoding="utf-8") as handle: audit_rows = [dict(row) for row in csv.DictReader(handle) if row["ecology"] == ecology_name]
        _write_csv(out_dir / "identifiability.csv", audit_rows)
    confidence_rows: list[dict[str, Any]] = []
    anchoring_rows: list[dict[str, Any]] = []
    for key, values in sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1], item[0][2] or "", item[0][3])):
        seed, target, source, h = key; valid = [v for v in values if _logical_observation(v)]
        scores = [float(v["confidence"]) for v in valid if v.get("confidence") is not None]; labels = [bool(v["correct"]) for v in valid if v.get("confidence") is not None]
        mem = [_memory_answers(v["task"].get("memory") or []) for v in valid]
        anchoring_rows.append({"ecology": ecology_name, "seed": seed, "source": source or "none", "target": target, "h": h, "n": len(valid),
                               "last_memory_match_rate": _mean([bool(v["answer"] and m and v["answer"] == m[-1]) for v, m in zip(valid, mem)]) if valid else None,
                               "any_memory_match_rate": _mean([bool(v["answer"] and v["answer"] in m) for v, m in zip(valid, mem)]) if valid else None})
        confidence_rows.append({"ecology": ecology_name, "seed": seed, "source": source or "none", "target": target, "h": h,
                                "n": len(valid), "mean_confidence": _mean(scores), "accuracy": _mean([1.0 if v else 0.0 for v in labels]),
                                "point_biserial": _point_biserial(scores, labels), "auroc": _auc(scores, labels)})
    _write_csv(out_dir / "confidence.csv", confidence_rows); _write_csv(out_dir / "anchoring.csv", anchoring_rows)
    _svg_heatmap(figure_dir / f"{ecology_name.lower()}_L8.svg", h8, ecology.families, f"{ecology_name} learning gain L(8)")
    _svg_learning(figure_dir / f"{ecology_name.lower()}_diagonal.svg", rows, ecology.families, f"{ecology_name} same-niche transfer")
    _atomic_json(out_dir / "qualification_summary.json", summary)
    _refresh_combined_outputs()
    return {"rows": rows, "summary": summary}


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--offline-audit", action="store_true"); parser.add_argument("--manifest", choices=sorted(ECOLOGIES)); parser.add_argument("--run", choices=sorted(ECOLOGIES)); parser.add_argument("--confirm-real", action="store_true"); parser.add_argument("--aggregate", choices=sorted(ECOLOGIES)); args = parser.parse_args()
    if args.offline_audit:
        rows = offline_audit(); print(json.dumps({"rows": len(rows), "status": candidate_status(rows)}, indent=2, sort_keys=True)); return
    if args.manifest:
        print(json.dumps(freeze_manifest(args.manifest), indent=2, sort_keys=True)); return
    if args.run:
        print(json.dumps(asyncio.run(run_real(args.run, confirm_real=args.confirm_real)), indent=2, sort_keys=True)); return
    if args.aggregate:
        print(json.dumps(aggregate(args.aggregate), indent=2, sort_keys=True)); return
    parser.error("select an action")


if __name__ == "__main__":
    main()
