"""Harness-neutral Observable Ecology Learner Calibration V2.

V2 preserves V3.1 and the V1 natural histories, but removes the concrete answer
vector from every static instruction and uses one exactly input-balanced,
history-disjoint eight-case probe support per seed.
"""

from __future__ import annotations

import argparse
import asyncio
import collections
import csv
import fcntl
import itertools
import json
import math
import os
import statistics
import subprocess
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from . import observable_learner_calibration as v1
from .credentials import CredentialStore
from .ecological_information import FAMILIES, GEOMETRIES, V3Case, all_symbolic_cases, generate_environment, posterior_predictive, sample_history, solve
from .ecological_information_v31 import EVAL_TEMPLATE_IDS, TRAIN_TEMPLATE_IDS, observable_o, render_observable
from .models import BackendResponse
from .providers import DeepSeekDirectBackend

ROOT = Path(__file__).resolve().parents[2]
REPORT_ROOT = ROOT / "reports/task-ecology/observable-learner-calibration-v2"
DATA_ROOT = ROOT / "data/auto-research/observable-learner-calibration-v2"
V31_ROOT = ROOT / "reports/task-ecology/ecological-information-v31"
V1_DATA_ROOT = ROOT / "data/auto-research/observable-learner-calibration-v1"
V1_REPORT_ROOT = ROOT / "reports/task-ecology/observable-learner-calibration-v1"
PROTOCOL = "OBSERVABLE-ECOLOGY-LEARNER-CALIBRATION-V2"
MODEL = "deepseek-v4-flash"
SEEDS = (9201, 9202, 9203, 9204)
H = 8
PROBE_COUNT = 8
MAX_ATTEMPTS = 2
HARD_CAP_USD = 0.10
RESERVATION_USD = 0.00015
INPUT_PRICE = 0.14
CACHED_INPUT_PRICE = 0.0028
OUTPUT_PRICE = 0.28
SYSTEM_PROMPT = "You are a single-agent decision learner. Use resolved cases only as feedback-only memory."
OUTPUT_INSTRUCTION = (
    'Return only one JSON object with a single key named "decisions". '
    "Its value must be an array of exactly three integers, in the same order as the three requested decisions. "
    "Each integer must be either 0 or 1. Use 1 when the corresponding action should be taken and 0 when it should not be taken. "
    "Do not include any other keys, explanation, markdown, or text."
)
RETRY_INSTRUCTION = "If the response cannot be represented in the required JSON schema, return a valid empty object so the harness can record the observation."
STATIC_INSTRUCTIONS = (SYSTEM_PROMPT, OUTPUT_INSTRUCTION, RETRY_INSTRUCTION)
RETRYABLE = {"parse_error", "empty_content", "transient_transport", "transport", "rate_limit", "server_error", "overloaded"}


def now() -> str:
    return datetime.now(UTC).isoformat()


def stable_hash(value: Any) -> str:
    return v1.stable_hash(value)


def atomic_json(path: Path, value: Any) -> None:
    v1.atomic_json(path, value)


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    v1.write_csv(path, rows, fields)


def static_instruction_triplets() -> list[str]:
    """Return static strings only; memory labels are intentionally excluded."""
    return list(STATIC_INSTRUCTIONS)


def static_triplet_leaks() -> list[str]:
    import re
    pattern = re.compile(r"\[\s*[01]\s*,\s*[01]\s*,\s*[01]\s*\]")
    return [text for text in STATIC_INSTRUCTIONS if pattern.search(text)]


def _case_record(family: str, x: tuple[int, int, int], y: tuple[int, int, int], template_id: int, role: str) -> dict[str, Any]:
    return {"case_id": f"{family}:{role}:t{template_id}:{''.join(map(str, x))}", "family": family,
            "x": list(x), "y": list(y), "template_id": template_id, "role": role}


def history_for(geometry: str, seed: int, source: str) -> list[dict[str, Any]]:
    env = generate_environment(geometry, seed)
    rng = __import__("random").Random(0x31A7 + seed * 1009 + sum(map(ord, source)) * 17)
    cases = sample_history(env, source, H, rng)
    return [_case_record(source, case.x, case.y, TRAIN_TEMPLATE_IDS[i % len(TRAIN_TEMPLATE_IDS)], "memory") for i, case in enumerate(cases)]


def _balanced_probe_x(seed: int) -> tuple[tuple[int, int, int], ...]:
    histories = {source: history_for("GLOBAL", seed, source) for source in FAMILIES}
    excluded = {tuple(record["x"]) for values in histories.values() for record in values}
    candidates = [tuple(case.x) for family in FAMILIES for case in all_symbolic_cases(family) if tuple(case.x) not in excluded]
    candidates = sorted(set(candidates))
    counts = [collections.Counter() for _ in range(3)]
    chosen: list[tuple[int, int, int]] = []

    def search(start: int) -> bool:
        if len(chosen) == PROBE_COUNT:
            return all(all(counts[j][value] == 2 for value in range(4)) for j in range(3))
        remaining = PROBE_COUNT - len(chosen)
        if len(candidates) - start < remaining:
            return False
        for index in range(start, len(candidates)):
            x = candidates[index]
            if any(counts[j][x[j]] >= 2 for j in range(3)):
                continue
            chosen.append(x)
            for j in range(3): counts[j][x[j]] += 1
            if search(index + 1): return True
            for j in range(3): counts[j][x[j]] -= 1
            chosen.pop()
        return False

    if not search(0):
        raise RuntimeError(f"no balanced V2 probe support for seed {seed}")
    return tuple(chosen)


def probe_design() -> dict[int, tuple[tuple[int, int, int], ...]]:
    designs = {seed: _balanced_probe_x(seed) for seed in SEEDS}
    # The same source X stream must be shared by all three geometries.
    for seed in SEEDS:
        for source in FAMILIES:
            streams = [tuple(tuple(row["x"]) for row in history_for(g, seed, source)) for g in GEOMETRIES]
            if len(set(streams)) != 1:
                raise RuntimeError(f"history stream differs across geometries: {seed}/{source}")
            if set(designs[seed]) & set(streams[0]):
                raise RuntimeError(f"probe/history overlap: {seed}/{source}")
    return designs


def _render(record: dict[str, Any]) -> str:
    family = record["family"]; return render_observable(observable_o(family, tuple(record["x"])), family, int(record["template_id"]))


def render_user(task: dict[str, Any]) -> str:
    memory = task.get("memory") or []
    parts = []
    if memory:
        parts.append("Prior resolved cases:\n" + "\n\n".join(_render(item) + f"\nResolved decision: {json.dumps(item['y'], separators=(',', ':'))}" for item in memory))
    parts.append("CURRENT CASE:\n" + _render(task["probe"]))
    parts.append(OUTPUT_INSTRUCTION)
    return "\n\n".join(parts)


def _lstar_population() -> dict[tuple[str, str, str], dict[str, float]]:
    return v1._load_lstar()


def exact_bayes(task: dict[str, Any]) -> dict[str, Any]:
    if task["condition"] == "baseline":
        return {"A_star_prompt": 0.125, "p_true": 0.125, "posterior_entropy": 3.0, "map_tie_count": 8, "true_in_map": True, "posterior": [0.125] * 8}
    env = generate_environment(task["geometry"], int(task["seed"]))
    history = [V3Case(item["family"], tuple(item["x"]), tuple(item["y"])) for item in task["memory"]]
    x = tuple(task["probe"]["x"]); target = task["target"]
    posterior = tuple(float(v) for v in posterior_predictive(env, task["source"], target, history, x))
    maximum = max(posterior); truth = tuple(task["probe"]["y"]); labels = list(itertools.product((0, 1), repeat=3)); map_indices = [i for i, value in enumerate(posterior) if abs(value - maximum) <= 1e-12]
    return {"A_star_prompt": maximum, "p_true": posterior[labels.index(truth)], "posterior_entropy": -sum(p * math.log2(p) for p in posterior if p > 0), "map_tie_count": len(map_indices), "true_in_map": labels.index(truth) in map_indices, "posterior": list(posterior)}


def expected_calls() -> dict[str, int]:
    baseline = 3 * 4 * 4 * 8; transfer = 3 * 4 * 4 * 4 * 8
    return {"baseline": baseline, "transfer": transfer, "total": baseline + transfer}


def _bayes_gate(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    informative: dict[str, list[float]] = {g: [] for g in GEOMETRIES}; independent: list[float] = []
    for task in tasks:
        if task["condition"] != "transfer": continue
        source, target, geometry = task["source"], task["target"], task["geometry"]
        block = (source in ("ACCESS", "RELEASE")) == (target in ("ACCESS", "RELEASE"))
        is_info = geometry == "GLOBAL" or (geometry == "BLOCK" and block) or (geometry == "DIAGONAL" and source == target)
        if is_info: informative[geometry].append(float(task["A_star_prompt"]))
        else: independent.append(float(task["A_star_prompt"]))
    summary = {g: statistics.mean(values) for g, values in informative.items()}
    independent_ok = all(abs(value - 0.125) <= 1e-12 for value in independent)
    return {"informative_mean_A_star": summary, "independent_min": min(independent), "independent_max": max(independent), "independent_exact": independent_ok, "pass": all(value >= .85 for value in summary.values()) and independent_ok}


def _recent_forecast(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    events = v1._load_events(V1_DATA_ROOT / "events.jsonl")
    means = {}
    for condition in ("baseline", "transfer"):
        values = [float(e["attempt_cost_usd"]) for e in events if e["task"]["condition"] == condition]
        means[condition] = statistics.mean(values) if values else 0.0
    projected = means["baseline"] * 384 + means["transfer"] * 1536
    chars = [len(SYSTEM_PROMPT) + len(render_user(task)) for task in tasks]
    return {"logical_calls": len(tasks), "projected_from_v1_observed_cost_usd": projected, "safety_margin_50pct_usd": projected * 1.5, "hard_cap_usd": HARD_CAP_USD, "within_cap_with_margin": projected * 1.5 <= HARD_CAP_USD, "min_prompt_chars": min(chars), "max_prompt_chars": max(chars), "mean_prompt_chars": statistics.mean(chars), "v1_mean_cost_by_condition": means}


def build_tasks() -> list[dict[str, Any]]:
    designs = probe_design(); lstar = _lstar_population(); tasks = []
    for geometry in GEOMETRIES:
        for seed in SEEDS:
            histories = {source: history_for(geometry, seed, source) for source in FAMILIES}
            for target in FAMILIES:
                for x in designs[seed]:
                    env = generate_environment(geometry, seed); y = solve(env.theta_by_family[target], x); probe = _case_record(target, x, y, EVAL_TEMPLATE_IDS[0], "probe")
                    task = {"condition": "baseline", "geometry": geometry, "seed": seed, "source": None, "target": target, "probe": probe, "memory": [], "h": 0}; task.update(lstar[(geometry, target, target)]); task.update(exact_bayes(task)); task["prompt_hash"] = stable_hash({"system": SYSTEM_PROMPT, "user": render_user(task)}); tasks.append(task)
            for source in FAMILIES:
                for target in FAMILIES:
                    for x in designs[seed]:
                        env = generate_environment(geometry, seed); y = solve(env.theta_by_family[target], x); probe = _case_record(target, x, y, EVAL_TEMPLATE_IDS[0], "probe")
                        task = {"condition": "transfer", "geometry": geometry, "seed": seed, "source": source, "target": target, "probe": probe, "memory": histories[source], "h": H}; task.update(lstar[(geometry, source, target)]); task.update(exact_bayes(task)); task["prompt_hash"] = stable_hash({"system": SYSTEM_PROMPT, "user": render_user(task)}); tasks.append(task)
    return tasks


def freeze_manifest() -> dict[str, Any]:
    if static_triplet_leaks(): raise RuntimeError("static instruction contains a concrete decision vector")
    verification = v1.verify_v31()
    if not verification["all_pass"]: raise RuntimeError(f"V3.1 gate failed: {verification['checks']}")
    tasks = build_tasks(); counts = {key: sum(task["condition"] == key for task in tasks) for key in ("baseline", "transfer")}; expected = expected_calls()
    if counts != {"baseline": expected["baseline"], "transfer": expected["transfer"]} or len(tasks) != expected["total"]: raise RuntimeError(f"V2 count mismatch {counts}/{len(tasks)}")
    bayes = _bayes_gate(tasks); forecast = _recent_forecast(tasks)
    if not bayes["pass"]: raise RuntimeError(f"exact Bayes gate failed: {bayes}")
    if not forecast["within_cap_with_margin"]: raise RuntimeError(f"V2 cost forecast exceeds hard cap: {forecast}")
    designs = probe_design()
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    write_csv(
        REPORT_ROOT / "probe_design.csv",
        [{"seed": seed, "probe_index": i, "x1": x[0], "x2": x[1], "x3": x[2]}
         for seed, xs in designs.items() for i, x in enumerate(xs)],
    )
    balance_rows = []
    for seed, xs in designs.items():
        for geometry in GEOMETRIES:
            for family in FAMILIES:
                env = generate_environment(geometry, seed)
                y_values = [solve(env.theta_by_family[family], x) for x in xs]
                balance_rows.append({
                    "seed": seed,
                    "geometry": geometry,
                    "family": family,
                    "unique_probes": len(set(xs)),
                    "history_overlap": int(any(tuple(x) in {tuple(item["x"]) for source in FAMILIES for item in history_for(geometry, seed, source)} for x in xs)),
                    "x1_counts": json.dumps([sum(x[0] == value for x in xs) for value in range(4)]),
                    "x2_counts": json.dumps([sum(x[1] == value for x in xs) for value in range(4)]),
                    "x3_counts": json.dumps([sum(x[2] == value for x in xs) for value in range(4)]),
                    "y1_counts": json.dumps([sum(y[0] == value for y in y_values) for value in range(2)]),
                    "y2_counts": json.dumps([sum(y[1] == value for y in y_values) for value in range(2)]),
                    "y3_counts": json.dumps([sum(y[2] == value for y in y_values) for value in range(2)]),
                })
    write_csv(REPORT_ROOT / "probe_balance_audit.csv", balance_rows)
    manifest = {"protocol": PROTOCOL, "created_at_utc": now(), "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "provider": "deepseek_direct", "model": MODEL, "thinking": "off", "seeds": list(SEEDS), "geometries": list(GEOMETRIES), "families": list(FAMILIES), "h": H, "probe_count": PROBE_COUNT, "logical_calls": expected["total"], "call_breakdown": expected, "hard_cap_usd": HARD_CAP_USD, "static_instruction_hash": stable_hash(list(STATIC_INSTRUCTIONS)), "probe_design": {str(seed): [list(x) for x in xs] for seed, xs in designs.items()}, "bayes_gate": bayes, "cost_forecast": forecast, "tasks": tasks}
    manifest["tasks_hash"] = stable_hash(tasks); path = REPORT_ROOT / "manifest.json"
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        if old.get("tasks_hash") != manifest["tasks_hash"]: raise RuntimeError("existing V2 manifest differs")
        return old
    atomic_json(path, manifest); return manifest


def _budget_change(*, reserve: float = 0.0, release: float = 0.0, actual: float = 0.0) -> dict[str, Any]:
    path = DATA_ROOT / "campaign_budget.json"; lock_path = path.with_suffix(".lock"); path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        budget = json.loads(path.read_text()) if path.exists() else {"protocol": PROTOCOL, "hard_cap_usd": HARD_CAP_USD, "spent_usd": 0.0, "reserved_usd": 0.0}
        spent, held = float(budget.get("spent_usd", 0)), float(budget.get("reserved_usd", 0))
        if held + 1e-12 < release or spent + held - release + reserve + actual > HARD_CAP_USD + 1e-12: raise RuntimeError("V2 hard budget guard")
        budget.update(reserved_usd=held - release + reserve, spent_usd=spent + actual, updated_at_utc=now()); atomic_json(path, budget); return budget


def _append_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle: handle.write(json.dumps(event, sort_keys=True) + "\n"); handle.flush(); os.fsync(handle.fileno())


def _cost(response: BackendResponse) -> float | None:
    from .costs import estimate_usage_cost
    return estimate_usage_cost(response.token_usage, input_per_million_tokens=INPUT_PRICE, cached_input_per_million_tokens=CACHED_INPUT_PRICE, output_per_million_tokens=OUTPUT_PRICE)


async def run_real(*, confirm_real: bool = False) -> dict[str, Any]:
    if not confirm_real: raise SystemExit("V2 real execution requires --confirm-real")
    manifest = json.loads((REPORT_ROOT / "manifest.json").read_text(encoding="utf-8")); events_path = DATA_ROOT / "events.jsonl"; status_path = DATA_ROOT / "run_status.json"
    if manifest.get("logical_calls") != 1920 or manifest.get("tasks_hash") != stable_hash(manifest["tasks"]): raise RuntimeError("V2 manifest integrity failure")
    events = v1._load_events(events_path); done = {e["logical_id"] for e in events if e.get("terminal")}; attempts = defaultdict(int)
    for event in events: attempts[event["logical_id"]] = max(attempts[event["logical_id"]], int(event.get("attempt", 0)) + 1)
    status = json.loads(status_path.read_text()) if status_path.exists() else {"protocol": PROTOCOL, "status": "initialized", "tasks_hash": manifest["tasks_hash"], "logical_calls": 1920, "created_at_utc": now()}
    if status.get("tasks_hash") != manifest["tasks_hash"]: raise RuntimeError("V2 status/manifest mismatch")
    status.update(status="running", started_or_resumed_at_utc=now()); atomic_json(status_path, status)
    backend = None; cost_total = sum(float(e.get("attempt_cost_usd") or 0) for e in events); retries = sum(int(e.get("attempt", 0)) for e in events)
    try:
        key = CredentialStore().get(source="keychain"); backend = DeepSeekDirectBackend(api_key=key, thinking="off", max_tokens=32)
        for task in manifest["tasks"]:
            logical_id = stable_hash({"protocol": PROTOCOL, "tasks_hash": manifest["tasks_hash"], "task": task})
            if logical_id in done: continue
            start = attempts.get(logical_id, 0)
            if start >= MAX_ATTEMPTS: raise RuntimeError(f"retry exhaustion {logical_id}")
            for attempt in range(start, MAX_ATTEMPTS):
                _budget_change(reserve=RESERVATION_USD)
                try:
                    response = await backend.complete(system_prompt=SYSTEM_PROMPT, user_prompt=render_user(task), model=MODEL, model_parameters={"thinking": "off", "max_tokens": 32})
                except Exception:
                    # A Python/provider exception can occur after the reservation
                    # but before a BackendResponse exists.  Release only this
                    # attempt's hold; the outer status journal remains incomplete.
                    _budget_change(release=RESERVATION_USD)
                    raise
                try:
                    cost = _cost(response)
                except Exception:
                    _budget_change(release=RESERVATION_USD)
                    raise
                if cost is None: _budget_change(release=RESERVATION_USD); raise RuntimeError("V2 usage/cost unavailable")
                _budget_change(release=RESERVATION_USD, actual=cost); cost_total += cost
                decisions, parse_category = v1.parse_decisions(response.raw_response); provider = response.provider_metadata or {}
                if provider.get("model") != MODEL: raise RuntimeError(f"model mismatch {provider.get('model')!r}")
                category = response.error_category or parse_category; error = response.error or parse_category; terminal = category == "out_of_domain" or (error is None and decisions is not None)
                event = {"protocol": PROTOCOL, "logical_id": logical_id, "attempt": attempt, "task": task, "decisions": decisions, "expected": task["probe"]["y"], "correct": decisions == task["probe"]["y"] if decisions is not None else False, "error": error, "error_category": category, "terminal": terminal, "raw_model_response": response.raw_response, "latency_s": response.latency_s, "token_usage": response.token_usage, "provider_metadata": provider, "attempt_cost_usd": cost, "finished_at_utc": now()}
                _append_event(events_path, event)
                events.append(event)
                if terminal: done.add(logical_id); break
                if not response.retryable or category not in RETRYABLE: raise RuntimeError(f"non-retryable V2 response {category}")
                retries += 1
            else: raise RuntimeError(f"retry exhaustion {logical_id}")
        if len(done) != 1920: raise RuntimeError(f"V2 coverage {len(done)}/1920")
        status.update(status="completed", physical_attempts=len(events), retries=retries, observed_cost_usd=cost_total, finished_at_utc=now())
    except Exception as exc:
        status.update(status="incomplete", failure=f"{type(exc).__name__}: {exc}", physical_attempts=len(events), retries=retries, observed_cost_usd=cost_total, finished_at_utc=now())
    finally:
        if backend is not None: await backend.close()
        atomic_json(status_path, status)
    return status


def _terminal(manifest: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events: grouped[event["logical_id"]].append(event)
    result = {}
    for task in manifest["tasks"]:
        lid = stable_hash({"protocol": PROTOCOL, "tasks_hash": manifest["tasks_hash"], "task": task}); values = [e for e in grouped.get(lid, []) if e.get("terminal")]
        if values: result[lid] = values[-1]
    return result


def _matrix(rows: list[dict[str, Any]], field: str) -> np.ndarray:
    result = np.zeros((4, 4)); index = {f: i for i, f in enumerate(FAMILIES)}
    for row in rows: result[index[row["source"]], index[row["target"]]] = float(row[field])
    return result


def _spearman(a: np.ndarray, b: np.ndarray) -> float | None:
    if len(set(a.ravel())) < 2 or len(set(b.ravel())) < 2: return None
    def rank(values):
        order = sorted(range(len(values)), key=lambda i: values[i]); output = [0.0] * len(values); i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]: j += 1
            for k in range(i, j + 1): output[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return np.asarray(output)
    return v1._cosine(rank(list(a.ravel())), rank(list(b.ravel())))


def analyze() -> dict[str, Any]:
    manifest = json.loads((REPORT_ROOT / "manifest.json").read_text()); events = v1._load_events(DATA_ROOT / "events.jsonl"); terminal = _terminal(manifest, events)
    if len(terminal) < manifest["logical_calls"]: raise RuntimeError(f"V2 incomplete {len(terminal)}/1920")
    baseline, transfer, response_rows = {}, [], []
    for task in manifest["tasks"]:
        lid = stable_hash({"protocol": PROTOCOL, "tasks_hash": manifest["tasks_hash"], "task": task}); event = terminal[lid]; decisions = event.get("decisions"); expected = task["probe"]["y"]
        row = {"geometry": task["geometry"], "seed": task["seed"], "condition": task["condition"], "source": task["source"] or "", "target": task["target"], "probe_id": task["probe"]["case_id"], "x": json.dumps(task["probe"]["x"]), "expected": json.dumps(expected), "decisions": json.dumps(decisions) if decisions is not None else "", "correct": int(decisions == expected) if decisions is not None else 0, "A_star_prompt": task["A_star_prompt"], "p_true": task["p_true"], "true_in_map": task["true_in_map"], "error_category": event.get("error_category") or "", "latency_s": event.get("latency_s"), "cost_usd": event.get("attempt_cost_usd"), "model": (event.get("provider_metadata") or {}).get("model", "")}
        response_rows.append(row)
        if task["condition"] == "baseline": baseline[(task["geometry"], task["seed"], task["target"], task["probe"]["case_id"])] = {"correct": row["correct"], "decisions": decisions, "expected": expected}
        else: transfer.append({"task": task, "event": event, "decisions": decisions, "correct": row["correct"]})
    write_csv(REPORT_ROOT / "response_level.csv", response_rows)
    seed_rows: list[dict[str, Any]] = []; component_rows: list[dict[str, Any]] = []; anchoring_rows: list[dict[str, Any]] = []; aggregate_rows: list[dict[str, Any]] = []
    for geometry in GEOMETRIES:
        for seed in SEEDS:
            for source in FAMILIES:
                for target in FAMILIES:
                    vals = [item for item in transfer if item["task"]["geometry"] == geometry and item["task"]["seed"] == seed and item["task"]["source"] == source and item["task"]["target"] == target]
                    base = [baseline[(geometry, seed, target, item["task"]["probe"]["case_id"])] for item in vals]
                    bacc = statistics.mean(item["correct"] for item in base); tacc = statistics.mean(item["correct"] for item in vals); astar = statistics.mean(item["task"]["A_star_prompt"] for item in vals)
                    seed_rows.append({"geometry": geometry, "seed": seed, "source": source, "target": target, "baseline_accuracy": bacc, "transfer_accuracy": tacc, "L_DS": tacc - bacc, "L_star_exact": astar - .125, "A_star_exact": astar, "n": len(vals)})
                    for bit in range(3):
                        bcomp = statistics.mean(int(item["decisions"] is not None and item["decisions"][bit] == item["expected"][bit]) for item in base); tcomp = statistics.mean(int(item["decisions"] is not None and item["decisions"][bit] == item["task"]["probe"]["y"][bit]) for item in vals)
                        component_rows.append({"geometry": geometry, "seed": seed, "source": source, "target": target, "component": bit + 1, "baseline_accuracy": bcomp, "transfer_accuracy": tcomp, "L_DS": tcomp - bcomp})
                    labels = [m["y"] for m in vals[0]["task"]["memory"]] if vals else []
                    for item in vals:
                        mem_labels = [m["y"] for m in item["task"]["memory"]]; decisions = item["decisions"]; counts = collections.Counter(tuple(label) for label in mem_labels)
                        anchoring_rows.append({"geometry": geometry, "seed": seed, "source": source, "target": target, "correct": item["correct"], "last_action_copy": int(bool(mem_labels and decisions == mem_labels[-1])) if decisions is not None else 0, "any_action_copy": int(any(decisions == label for label in mem_labels)) if decisions is not None else 0, "modal_memory_copy": int(bool(mem_labels and decisions == counts.most_common(1)[0][0])) if decisions is not None else 0, "component_last_copy": statistics.mean(int(decisions[bit] == mem_labels[-1][bit]) for bit in range(3)) if decisions is not None and mem_labels else None, "A_star_prompt": item["task"]["A_star_prompt"], "correct_when_Astar_ge_099": int(item["correct"] and item["task"]["A_star_prompt"] >= .99)})
    write_csv(REPORT_ROOT / "seed_level_transfer_matrices.csv", seed_rows); write_csv(REPORT_ROOT / "seed_level_accuracy.csv", seed_rows); write_csv(REPORT_ROOT / "component_transfer.csv", component_rows); write_csv(REPORT_ROOT / "anchoring.csv", anchoring_rows)
    matrices: dict[str, np.ndarray] = {}; lstar_matrices: dict[str, np.ndarray] = {}; alignments = []; summary: dict[str, Any] = {"geometries": {}, "qualification_gates": {}, "component_summary": {}}
    for geometry in GEOMETRIES:
        rows = [r for r in seed_rows if r["geometry"] == geometry]; agg = []
        for source in FAMILIES:
            for target in FAMILIES:
                vals = [float(r["L_DS"]) for r in rows if r["source"] == source and r["target"] == target]; ls = [float(r["L_star_exact"]) for r in rows if r["source"] == source and r["target"] == target]
                agg.append({"geometry": geometry, "source": source, "target": target, "L_DS": statistics.mean(vals), "L_star_exact": statistics.mean(ls), "seed_values": json.dumps(vals), "seed_mean": statistics.mean(vals), "seed_median": statistics.median(vals), "seed_min": min(vals), "seed_max": max(vals), "seed_sd": statistics.stdev(vals) if len(vals)>1 else 0.0})
        aggregate_rows.extend(agg); matrices[geometry] = _matrix(agg, "L_DS"); lstar_matrices[geometry] = _matrix(agg, "L_star_exact")
        ds, ls = matrices[geometry], lstar_matrices[geometry]; d = statistics.mean(ds[i,i] for i in range(4)); o = statistics.mean(ds[i,j] for i in range(4) for j in range(4) if i != j); item = {"D": d, "O": o, "Q": d-o, "O_over_D": o/d if d else None, "Q_Lstar_exact": statistics.mean(ls[i,i] for i in range(4))-statistics.mean(ls[i,j] for i in range(4) for j in range(4) if i != j)}
        if geometry == "BLOCK":
            w = statistics.mean([ds[0,1],ds[1,0],ds[2,3],ds[3,2]]); c = statistics.mean(ds[i,j] for i in range(4) for j in range(4) if i != j and ((i<2)!=(j<2))); item.update(W=w,C=c,B=w-c)
        summary["geometries"][geometry] = item
    write_csv(REPORT_ROOT / "aggregate_transfer_matrices.csv", aggregate_rows)
    exact_rows = []
    for task in manifest["tasks"]:
        exact_rows.append({"geometry": task["geometry"], "seed": task["seed"], "condition": task["condition"], "source": task["source"] or "", "target": task["target"], "probe_id": task["probe"]["case_id"], "A_star_prompt": task["A_star_prompt"], "p_true": task["p_true"], "posterior_entropy": task["posterior_entropy"], "map_tie_count": task["map_tie_count"], "true_in_map": task["true_in_map"], "posterior": json.dumps(task["posterior"])})
    write_csv(REPORT_ROOT / "exact_bayes_prompt_opportunity.csv", exact_rows)
    for geometry in GEOMETRIES:
        ds, ls = matrices[geometry], lstar_matrices[geometry]; p = np.eye(4)-np.ones((4,4))/4; den = np.linalg.norm(p@ls@p); rawden = np.linalg.norm(ds)*np.linalg.norm(ls); alignments.append({"geometry": geometry, "raw_cosine": float(np.sum(ds*ls)/rawden) if rawden else None, "centered_cosine": float(np.sum((p@ds@p)*(p@ls@p))/(np.linalg.norm(p@ds@p)*den)) if den else None, "spearman": _spearman(ds,ls) if np.count_nonzero(ls) > 1 else None})
        v1._svg_heatmap(REPORT_ROOT / "figures" / f"L_DS_{geometry.lower()}.svg", ds, f"V2 L DeepSeek {geometry}"); v1._svg_heatmap(REPORT_ROOT / "figures" / f"Lstar_exact_{geometry.lower()}.svg", ls, f"V2 exact L* {geometry}")
    write_csv(REPORT_ROOT / "geometry_alignment.csv", alignments)
    zero = [r for r in aggregate_rows if (r["geometry"] == "BLOCK" and ((r["source"] in ("ACCESS","RELEASE")) != (r["target"] in ("ACCESS","RELEASE")))) or (r["geometry"] == "DIAGONAL" and r["source"] != r["target"])]
    write_csv(REPORT_ROOT / "zero_information_transfer.csv", zero)
    distribution = []
    for condition in ("baseline", "transfer"):
        values = [tuple(json.loads(r["decisions"])) for r in response_rows if r["condition"] == condition]; counts = collections.Counter(values); total = len(values); entropy = -sum((n/total)*math.log2(n/total) for n in counts.values())
        distribution.append({"condition": condition, "n": total, "modal_output": json.dumps(list(counts.most_common(1)[0][0])), "modal_fraction": counts.most_common(1)[0][1]/total, "output_entropy_bits": entropy, "p_010": counts[(0,1,0)]/total, "bit1_one_rate": sum(v[0] for v in values)/total, "bit2_one_rate": sum(v[1] for v in values)/total, "bit3_one_rate": sum(v[2] for v in values)/total})
    for condition in ("same_niche_transfer", "cross_niche_transfer"):
        values = [tuple(json.loads(r["decisions"])) for r in response_rows if r["condition"] == "transfer" and ((r["source"] == r["target"]) == (condition == "same_niche_transfer"))]; counts = collections.Counter(values); total=len(values); distribution.append({"condition": condition,"n":total,"modal_output":json.dumps(list(counts.most_common(1)[0][0])),"modal_fraction":counts.most_common(1)[0][1]/total,"output_entropy_bits":-sum((n/total)*math.log2(n/total) for n in counts.values()),"p_010":counts[(0,1,0)]/total})
    write_csv(REPORT_ROOT / "response_distribution.csv", distribution)
    q = {g: summary["geometries"][g]["Q"] for g in GEOMETRIES}; gates = {"useful_local_learning": all(summary["geometries"][g]["D"] >= .10 for g in GEOMETRIES), "global_dense_transfer": summary["geometries"]["GLOBAL"]["O"] > 0 and summary["geometries"]["GLOBAL"]["O_over_D"] is not None and summary["geometries"]["GLOBAL"]["O_over_D"] >= .5, "block_structure": summary["geometries"]["BLOCK"].get("W",0) > 0 and summary["geometries"]["BLOCK"].get("B",0) >= .05, "diagonal_locality": summary["geometries"]["DIAGONAL"]["D"] > 0 and summary["geometries"]["DIAGONAL"]["O_over_D"] <= .5, "Q_ordering": q["GLOBAL"] < q["BLOCK"] < q["DIAGONAL"], "bayes_geometry_alignment": any((r["raw_cosine"] is not None and r["raw_cosine"] > 0) or (r["centered_cosine"] is not None and r["centered_cosine"] > 0) for r in alignments)}; summary["qualification_gates"] = {k:{"status":"PASS" if val else "FAIL"} for k,val in gates.items()}; summary["overall_status"] = "QUALIFIED" if all(gates.values()) else ("PARTIAL" if any(gates.values()) else "NOT_QUALIFIED")
    technical_categories = RETRYABLE | {"transport", "server_error", "invalid_model", "budget_guard"}
    has_technical_error = any(e.get("error_category") in technical_categories for e in events)
    health = {"protocol": PROTOCOL, "logical_expected": 1920, "logical_terminal": len(terminal), "physical_attempts": len(events), "technical_retries": sum(int(e.get("attempt",0)) for e in events), "semantic_ood": sum(e.get("error_category") == "out_of_domain" for e in events), "coverage": len(terminal)/1920, "models": sorted({(e.get("provider_metadata") or {}).get("model") for e in events}), "fingerprints": sorted({(e.get("provider_metadata") or {}).get("system_fingerprint") for e in events}), "observed_cost_usd": sum(float(e.get("attempt_cost_usd") or 0) for e in events), "usage_coverage": sum(bool(e.get("token_usage")) for e in events)/len(events), "latency_mean_s": statistics.mean(float(e.get("latency_s") or 0) for e in events), "latency_median_s": statistics.median(float(e.get("latency_s") or 0) for e in events), "input_tokens": sum(int((e.get("token_usage") or {}).get("prompt_tokens") or 0) for e in events), "cached_input_tokens": sum(int((e.get("token_usage") or {}).get("prompt_cache_hit_tokens") or 0) for e in events), "output_tokens": sum(int((e.get("token_usage") or {}).get("completion_tokens") or 0) for e in events), "classification": "CLEAN" if len(terminal)==1920 and not has_technical_error else "COMPLETE_WITH_RETRIES"}
    atomic_json(REPORT_ROOT / "qualification.json", summary); atomic_json(REPORT_ROOT / "technical_health.json", health); atomic_json(REPORT_ROOT / "cost.json", {"observed_cost_usd":health["observed_cost_usd"],"hard_cap_usd":HARD_CAP_USD,"remaining_usd":HARD_CAP_USD-health["observed_cost_usd"]})
    return {"summary": summary, "health": health, "alignment": alignments}


def main() -> None:
    parser = argparse.ArgumentParser(description=PROTOCOL); parser.add_argument("--freeze", action="store_true"); parser.add_argument("--run", action="store_true"); parser.add_argument("--confirm-real", action="store_true"); parser.add_argument("--analyze", action="store_true")
    args = parser.parse_args()
    if args.freeze:
        manifest = freeze_manifest(); print(json.dumps({"manifest": str(REPORT_ROOT/"manifest.json"), "tasks_hash":manifest["tasks_hash"], "calls":manifest["call_breakdown"], "bayes_gate":manifest["bayes_gate"], "forecast":manifest["cost_forecast"]}, indent=2))
    elif args.run: print(json.dumps(asyncio.run(run_real(confirm_real=args.confirm_real)), indent=2))
    elif args.analyze: print(json.dumps(analyze(), indent=2, default=float))
    else: parser.error("choose --freeze, --run, or --analyze")


if __name__ == "__main__": main()
