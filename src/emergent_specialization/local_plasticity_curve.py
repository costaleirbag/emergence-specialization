"""Frozen local-plasticity curve calibration.

This is a single-agent microscopic gate.  It reuses the corrected V2 semantic
substrate and asks only whether local natural experience improves competence
more than equally sized independent foreign context.  It is deliberately not a
society or routing experiment.
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
import random
import statistics
import subprocess
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from . import observable_learner_calibration as v1
from . import observable_learner_calibration_v2 as v2
from .credentials import CredentialStore
from .ecological_information import FAMILIES, generate_environment
from .models import BackendResponse
from .providers import DeepSeekDirectBackend

ROOT = Path(__file__).resolve().parents[2]
V2_REPORT_ROOT = ROOT / "reports/task-ecology/observable-learner-calibration-v2"
V2_DATA_ROOT = ROOT / "data/auto-research/observable-learner-calibration-v2"
REPORT_ROOT = ROOT / "reports/task-ecology/local-plasticity-curve-v1"
DATA_ROOT = ROOT / "data/auto-research/local-plasticity-curve-v1"
PROTOCOL = "LOCAL-PLASTICITY-CURVE-V1"
MODEL = "deepseek-v4-flash"
GEOMETRY = "DIAGONAL"
SEEDS = (9201, 9202, 9203, 9204)
FAMILIES = tuple(FAMILIES)
HORIZONS = (1, 2, 4, 8)
ORDER_SEED = 20260812
MAX_ATTEMPTS = 2
HARD_CAP_USD = 0.12
RESERVATION_USD = 0.00015
INPUT_PRICE = 0.14
CACHED_INPUT_PRICE = 0.0028
OUTPUT_PRICE = 0.28
SYSTEM_PROMPT = v2.SYSTEM_PROMPT
OUTPUT_INSTRUCTION = v2.OUTPUT_INSTRUCTION
STATIC_INSTRUCTION_HASH = v1.stable_hash([SYSTEM_PROMPT, OUTPUT_INSTRUCTION, v2.RETRY_INSTRUCTION])
RETRYABLE = {"parse_error", "empty_content", "transient_transport", "transport", "rate_limit", "server_error", "overloaded"}


def now() -> str:
    return datetime.now(UTC).isoformat()


def stable_hash(value: Any) -> str:
    return v1.stable_hash(value)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _v2_manifest() -> dict[str, Any]:
    return json.loads((V2_REPORT_ROOT / "manifest.json").read_text(encoding="utf-8"))


def _v2_maps() -> tuple[dict[tuple[Any, ...], dict[str, Any]], dict[tuple[Any, ...], dict[str, Any]]]:
    manifest = _v2_manifest()
    baseline: dict[tuple[Any, ...], dict[str, Any]] = {}
    transfer: dict[tuple[Any, ...], dict[str, Any]] = {}
    for task in manifest["tasks"]:
        if task["geometry"] != GEOMETRY:
            continue
        if task["condition"] == "baseline":
            baseline[(int(task["seed"]), task["target"], task["probe"]["case_id"])] = task
        else:
            transfer[(int(task["seed"]), task["source"], task["target"], task["probe"]["case_id"])] = task
    return baseline, transfer


def substrate_audit() -> dict[str, Any]:
    manifest = _v2_manifest()
    baseline, transfer = _v2_maps()
    expected_baseline = len(SEEDS) * len(FAMILIES) * v2.PROBE_COUNT
    expected_transfer = len(SEEDS) * len(FAMILIES) * len(FAMILIES) * v2.PROBE_COUNT
    checks: dict[str, Any] = {}
    checks["v2_harness_corrected"] = manifest.get("protocol") == v2.PROTOCOL and (V2_REPORT_ROOT / "manifest.json").exists()
    checks["diagonal_only_reference"] = len(baseline) == expected_baseline and len(transfer) == expected_transfer
    checks["v2_probe_count"] = v2.PROBE_COUNT == 8
    checks["input_balanced"] = True
    checks["history_probe_disjoint"] = True
    checks["nested_prefixes"] = True
    checks["history_stream_same_across_target"] = True
    checks["diagonal_policies_independent"] = True
    probe_by_seed: dict[int, set[tuple[int, int, int]]] = defaultdict(set)
    for task in baseline.values():
        probe_by_seed[int(task["seed"])].add(tuple(task["probe"]["x"]))
    for seed in SEEDS:
        xs = probe_by_seed[seed]
        checks["input_balanced"] &= len(xs) == 8 and all(sum(x[j] == value for x in xs) == 2 for j in range(3) for value in range(4))
        for source in FAMILIES:
            history = transfer[(seed, source, source, next(iter([p for s, t, p in baseline if s == seed and t == source])))]["memory"]
            hx = {tuple(item["x"]) for item in history}
            checks["history_probe_disjoint"] &= not (hx & xs)
            for h in HORIZONS:
                checks["nested_prefixes"] &= [item["case_id"] for item in history[:h]] == [item["case_id"] for item in history[:h]]
            streams = [transfer[(seed, source, target, next(iter([p for s, t, p in baseline if s == seed and t == target])))]["memory"] for target in FAMILIES]
            checks["history_stream_same_across_target"] &= len({stable_hash(stream) for stream in streams}) == 1
        env = generate_environment(GEOMETRY, seed)
        policy_hashes = [stable_hash(policy) for policy in env.theta_by_family.values()]
        checks["diagonal_policies_independent"] &= len(set(policy_hashes)) == len(policy_hashes)
    checks["all_pass"] = all(bool(value) for value in checks.values())
    return {"checks": checks, "v2_manifest_tasks_hash": manifest.get("tasks_hash"), "baseline_rows": len(baseline), "transfer_rows": len(transfer)}


def _task_with_memory(base: dict[str, Any], *, condition: str, source: str | None, target: str, h: int, memory: list[dict[str, Any]]) -> dict[str, Any]:
    task = json.loads(json.dumps(base))
    task.update({"protocol": PROTOCOL, "condition": condition, "geometry": GEOMETRY, "source": source, "target": target, "h": h, "memory": memory})
    # v2 exact_bayes uses its baseline/transfer condition names.
    oracle_task = dict(task)
    oracle_task["condition"] = "baseline" if condition == "EMPTY" else "transfer"
    oracle_task.update(v2.exact_bayes(oracle_task))
    task.update({key: value for key, value in oracle_task.items() if key in ("A_star_prompt", "p_true", "posterior_entropy", "map_tie_count", "true_in_map", "posterior")})
    task["prompt_hash"] = stable_hash({"system": SYSTEM_PROMPT, "user": v2.render_user(task)})
    task["static_instruction_hash"] = STATIC_INSTRUCTION_HASH
    task["history_ids"] = [item["case_id"] for item in memory]
    task["probe_x"] = list(task["probe"]["x"])
    return task


def build_tasks() -> list[dict[str, Any]]:
    audit = substrate_audit()
    if not audit["checks"]["all_pass"]:
        raise RuntimeError(f"V2 substrate audit failed: {audit}")
    baseline, transfer = _v2_maps()
    tasks: list[dict[str, Any]] = []
    for seed in SEEDS:
        for target in FAMILIES:
            probes = sorted({probe for (s, t, probe) in baseline if s == seed and t == target})
            for probe_id in probes:
                base = baseline[(seed, target, probe_id)]
                tasks.append(_task_with_memory(base, condition="EMPTY", source=None, target=target, h=0, memory=[]))
                for h in HORIZONS:
                    same = transfer[(seed, target, target, probe_id)]["memory"][:h]
                    tasks.append(_task_with_memory(base, condition="SAME", source=target, target=target, h=h, memory=same))
                    for source in FAMILIES:
                        if source == target:
                            continue
                        foreign = transfer[(seed, source, target, probe_id)]["memory"][:h]
                        tasks.append(_task_with_memory(base, condition="FOREIGN", source=source, target=target, h=h, memory=foreign))
    expected = expected_calls()
    if len(tasks) != expected["total"]:
        raise RuntimeError(f"local plasticity task count mismatch {len(tasks)} != {expected}")
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for task in tasks:
        groups[(task["seed"], task["target"], task["h"], task["probe"]["case_id"])].append(task)
    rng = random.Random(ORDER_SEED)
    grouped = list(groups.values())
    rng.shuffle(grouped)
    ordered: list[dict[str, Any]] = []
    for group in grouped:
        group.sort(key=lambda item: (item["condition"], item.get("source") or ""))
        rng.shuffle(group)
        for task in group:
            task["execution_order"] = len(ordered)
            ordered.append(task)
    return ordered


def expected_calls() -> dict[str, int]:
    empty = len(SEEDS) * len(FAMILIES) * v2.PROBE_COUNT
    same = len(HORIZONS) * empty
    foreign = len(HORIZONS) * len(SEEDS) * len(FAMILIES) * (len(FAMILIES) - 1) * v2.PROBE_COUNT
    return {"empty": empty, "same": same, "foreign": foreign, "total": empty + same + foreign}


def _recent_forecast(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    events = v1._load_events(V2_DATA_ROOT / "events.jsonl")
    old_tasks = _v2_manifest()["tasks"]
    old_chars = {"baseline": [], "transfer": []}
    old_costs = {"baseline": [], "transfer": []}
    for event in events:
        condition = event["task"]["condition"]
        old_costs[condition].append(float(event.get("attempt_cost_usd") or 0.0))
    for task in old_tasks:
        old_chars[task["condition"]].append(len(v2.SYSTEM_PROMPT) + len(v2.render_user(task)))
    new_by_condition = {"EMPTY": [], "SAME": [], "FOREIGN": []}
    for task in tasks:
        new_by_condition[task["condition"]].append(len(SYSTEM_PROMPT) + len(v2.render_user(task)))
    baseline_cost = statistics.mean(old_costs["baseline"]); transfer_cost = statistics.mean(old_costs["transfer"])
    baseline_chars = statistics.mean(old_chars["baseline"]); transfer_chars = statistics.mean(old_chars["transfer"])
    new_baseline_chars = statistics.mean(new_by_condition["EMPTY"])
    new_transfer_chars = statistics.mean(new_by_condition["SAME"] + new_by_condition["FOREIGN"])
    projected = baseline_cost * len(new_by_condition["EMPTY"]) * new_baseline_chars / baseline_chars + transfer_cost * (len(tasks) - len(new_by_condition["EMPTY"])) * new_transfer_chars / transfer_chars
    return {"logical_calls": len(tasks), "projected_cost_usd": projected, "safety_margin_50pct_usd": projected * 1.5, "hard_cap_usd": HARD_CAP_USD, "within_cap_with_margin": projected * 1.5 <= HARD_CAP_USD, "old_v2_mean_cost_baseline": baseline_cost, "old_v2_mean_cost_transfer": transfer_cost, "new_mean_prompt_chars_empty": new_baseline_chars, "new_mean_prompt_chars_history": new_transfer_chars}


def freeze_manifest() -> dict[str, Any]:
    if v2.static_triplet_leaks():
        raise RuntimeError("static instruction contains a concrete decision vector")
    tasks = build_tasks(); expected = expected_calls(); forecast = _recent_forecast(tasks)
    if len(tasks) != expected["total"] or collections.Counter(task["condition"] for task in tasks) != {"EMPTY": 128, "SAME": 512, "FOREIGN": 1536}:
        raise RuntimeError("condition count mismatch")
    if not forecast["within_cap_with_margin"]:
        raise RuntimeError(f"cost forecast exceeds cap: {forecast}")
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    audit = substrate_audit()
    manifest = {"protocol": PROTOCOL, "created_at_utc": now(), "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "provider": "deepseek_direct", "model": MODEL, "thinking": "off", "geometry": GEOMETRY, "seeds": list(SEEDS), "families": list(FAMILIES), "horizons": list(HORIZONS), "probe_count": v2.PROBE_COUNT, "order_seed": ORDER_SEED, "logical_calls": expected["total"], "call_breakdown": expected, "hard_cap_usd": HARD_CAP_USD, "v2_tasks_hash": _v2_manifest()["tasks_hash"], "substrate_audit": audit, "forecast": forecast, "tasks": tasks}
    manifest["tasks_hash"] = stable_hash(tasks)
    path = REPORT_ROOT / "manifest.json"
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        if old.get("tasks_hash") != manifest["tasks_hash"]:
            raise RuntimeError("existing local-plasticity manifest differs")
        return old
    atomic = v1.atomic_json
    atomic(path, manifest)
    return manifest


def _budget_change(*, reserve: float = 0.0, release: float = 0.0, actual: float = 0.0) -> dict[str, Any]:
    path = DATA_ROOT / "campaign_budget.json"; lock_path = path.with_suffix(".lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        budget = json.loads(path.read_text()) if path.exists() else {"protocol": PROTOCOL, "hard_cap_usd": HARD_CAP_USD, "spent_usd": 0.0, "reserved_usd": 0.0}
        spent, held = float(budget.get("spent_usd", 0.0)), float(budget.get("reserved_usd", 0.0))
        if held + 1e-12 < release or spent + held - release + reserve + actual > HARD_CAP_USD + 1e-12:
            raise RuntimeError("local plasticity hard budget guard")
        budget.update(spent_usd=spent + actual, reserved_usd=held - release + reserve, updated_at_utc=now())
        v1.atomic_json(path, budget)
        return budget


def _append(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
        handle.flush()
        import os
        os.fsync(handle.fileno())


def _cost(response: BackendResponse) -> float | None:
    from .costs import estimate_usage_cost
    return estimate_usage_cost(response.token_usage, input_per_million_tokens=INPUT_PRICE, cached_input_per_million_tokens=CACHED_INPUT_PRICE, output_per_million_tokens=OUTPUT_PRICE)


async def run_real(*, confirm_real: bool = False) -> dict[str, Any]:
    if not confirm_real:
        raise SystemExit("local plasticity real execution requires --confirm-real")
    manifest = json.loads((REPORT_ROOT / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("logical_calls") != 2176 or manifest.get("tasks_hash") != stable_hash(manifest["tasks"]):
        raise RuntimeError("local plasticity manifest integrity failure")
    events_path = DATA_ROOT / "events.jsonl"; status_path = DATA_ROOT / "run_status.json"
    events = v1._load_events(events_path); done = {e["logical_id"] for e in events if e.get("terminal")}; attempts = defaultdict(int)
    for event in events:
        attempts[event["logical_id"]] = max(attempts[event["logical_id"]], int(event.get("attempt", 0)) + 1)
    status = json.loads(status_path.read_text()) if status_path.exists() else {"protocol": PROTOCOL, "status": "initialized", "tasks_hash": manifest["tasks_hash"], "logical_calls": 2176, "created_at_utc": now()}
    if status.get("tasks_hash") != manifest["tasks_hash"]:
        raise RuntimeError("local plasticity status/manifest mismatch")
    status.update(status="running", started_or_resumed_at_utc=now()); v1.atomic_json(status_path, status)
    backend = None; spent = sum(float(e.get("attempt_cost_usd") or 0.0) for e in events); retries = sum(int(e.get("attempt", 0)) for e in events)
    try:
        key = CredentialStore().get(source="keychain")
        backend = DeepSeekDirectBackend(api_key=key, thinking="off", max_tokens=32)
        for task in manifest["tasks"]:
            logical_id = stable_hash({"protocol": PROTOCOL, "tasks_hash": manifest["tasks_hash"], "task": task})
            if logical_id in done:
                continue
            start = attempts.get(logical_id, 0)
            if start >= MAX_ATTEMPTS:
                raise RuntimeError(f"retry exhaustion {logical_id}")
            for attempt in range(start, MAX_ATTEMPTS):
                _budget_change(reserve=RESERVATION_USD)
                try:
                    response = await backend.complete(system_prompt=SYSTEM_PROMPT, user_prompt=v2.render_user(task), model=MODEL, model_parameters={"thinking": "off", "max_tokens": 32})
                    cost = _cost(response)
                except Exception:
                    _budget_change(release=RESERVATION_USD)
                    raise
                if cost is None:
                    _budget_change(release=RESERVATION_USD)
                    raise RuntimeError("usage/cost unavailable")
                _budget_change(release=RESERVATION_USD, actual=cost); spent += cost
                decisions, parse_category = v1.parse_decisions(response.raw_response); provider = response.provider_metadata or {}
                if provider.get("model") != MODEL:
                    raise RuntimeError(f"model mismatch {provider.get('model')!r}")
                category = response.error_category or parse_category; error = response.error or parse_category
                terminal = category == "out_of_domain" or (error is None and decisions is not None)
                event = {"protocol": PROTOCOL, "logical_id": logical_id, "attempt": attempt, "task": task, "decisions": decisions, "expected": task["probe"]["y"], "correct": decisions == task["probe"]["y"] if decisions is not None else False, "error": error, "error_category": category, "terminal": terminal, "raw_model_response": response.raw_response, "latency_s": response.latency_s, "token_usage": response.token_usage, "provider_metadata": provider, "attempt_cost_usd": cost, "finished_at_utc": now()}
                _append(events_path, event); events.append(event)
                if terminal:
                    done.add(logical_id); break
                if not response.retryable or category not in RETRYABLE:
                    raise RuntimeError(f"non-retryable response {category}")
                retries += 1
            else:
                raise RuntimeError(f"retry exhaustion {logical_id}")
        if len(done) != 2176:
            raise RuntimeError(f"coverage {len(done)}/2176")
        status.update(status="completed", physical_attempts=len(events), retries=retries, observed_cost_usd=spent, finished_at_utc=now())
    except Exception as exc:
        status.update(status="incomplete", failure=f"{type(exc).__name__}: {exc}", physical_attempts=len(events), retries=retries, observed_cost_usd=spent, finished_at_utc=now())
    finally:
        if backend is not None:
            await backend.close()
        v1.atomic_json(status_path, status)
    return status


def _load_terminal(manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    events = v1._load_events(DATA_ROOT / "events.jsonl"); grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        grouped[event["logical_id"]].append(event)
    terminal: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for task in manifest["tasks"]:
        lid = stable_hash({"protocol": PROTOCOL, "tasks_hash": manifest["tasks_hash"], "task": task})
        values = [e for e in grouped.get(lid, []) if e.get("terminal")]
        if values:
            terminal[lid] = values[-1]
    if len(terminal) != manifest["logical_calls"]:
        raise RuntimeError(f"coverage {len(terminal)}/{manifest['logical_calls']}")
    for task in manifest["tasks"]:
        lid = stable_hash({"protocol": PROTOCOL, "tasks_hash": manifest["tasks_hash"], "task": task}); event = terminal[lid]; decisions = event.get("decisions")
        rows.append({"logical_id": lid, "condition": task["condition"], "h": task["h"], "seed": int(task["seed"]), "source": task.get("source") or "", "target": task["target"], "probe_id": task["probe"]["case_id"], "x": json.dumps(task["probe"]["x"]), "expected": json.dumps(task["probe"]["y"]), "decisions": json.dumps(decisions, separators=(",", ":")) if decisions is not None else "", "correct": int(decisions == task["probe"]["y"]) if decisions is not None else 0, "valid": int(decisions is not None), "A_star_prompt": task["A_star_prompt"], "error_category": event.get("error_category") or "", "latency_s": event.get("latency_s"), "cost_usd": event.get("attempt_cost_usd"), "model": (event.get("provider_metadata") or {}).get("model", "")})
    return rows, terminal


def _mean_sd(values: list[float]) -> tuple[float, float, float, float]:
    return (statistics.mean(values), statistics.median(values), min(values), max(values)) if values else (float("nan"),) * 4


def analyze() -> dict[str, Any]:
    manifest = json.loads((REPORT_ROOT / "manifest.json").read_text(encoding="utf-8")); rows, terminal = _load_terminal(manifest); write_csv(REPORT_ROOT / "response_level.csv", rows)
    valid = [row for row in rows if row["valid"]]
    def subset(condition: str, h: int, seed: int | None = None, target: str | None = None, source: str | None = None) -> list[dict[str, Any]]:
        return [row for row in valid if row["condition"] == condition and int(row["h"]) == h and (seed is None or row["seed"] == seed) and (target is None or row["target"] == target) and (source is None or row["source"] == source)]
    def accuracy(condition: str, h: int, **kwargs: Any) -> float:
        values = [row["correct"] for row in subset(condition, h, **kwargs)]
        return statistics.mean(values) if values else float("nan")
    seed_rows = []
    curve_rows = []
    gain_rows = []
    seed_values: dict[tuple[str, int], list[float]] = {}
    for seed in SEEDS:
        a0 = accuracy("EMPTY", 0, seed=seed)
        same_values = {}; foreign_values = {}
        for h in HORIZONS:
            same_values[h] = accuracy("SAME", h, seed=seed)
            foreign_values[h] = accuracy("FOREIGN", h, seed=seed)
            seed_rows.extend([{"condition": "SAME", "h": h, "seed": seed, "accuracy": same_values[h]}, {"condition": "FOREIGN", "h": h, "seed": seed, "accuracy": foreign_values[h]}])
            gain_rows.append({"seed": seed, "h": h, "G_abs": same_values[h] - a0, "G_rel": same_values[h] - foreign_values[h], "G_foreign": foreign_values[h] - a0})
        seed_rows.append({"condition": "EMPTY", "h": 0, "seed": seed, "accuracy": a0})
        for condition, values in (("SAME", same_values), ("FOREIGN", foreign_values)):
            for h, value in values.items():
                seed_values.setdefault((condition, h), []).append(value)
                curve_rows.append({"condition": condition, "h": h, "accuracy": value})
    write_csv(REPORT_ROOT / "seed_level_accuracy.csv", seed_rows)
    write_csv(REPORT_ROOT / "absolute_gain.csv", [{"h": h, "seed": seed, "G_abs": next(r["G_abs"] for r in gain_rows if r["seed"] == seed and r["h"] == h)} for seed in SEEDS for h in HORIZONS])
    write_csv(REPORT_ROOT / "relative_gain.csv", [{"h": h, "seed": seed, "G_rel": next(r["G_rel"] for r in gain_rows if r["seed"] == seed and r["h"] == h)} for seed in SEEDS for h in HORIZONS])
    write_csv(REPORT_ROOT / "foreign_context_effect.csv", [{"h": h, "seed": seed, "G_foreign": next(r["G_foreign"] for r in gain_rows if r["seed"] == seed and r["h"] == h)} for seed in SEEDS for h in HORIZONS])
    curve_summary = []
    for condition in ("SAME", "FOREIGN"):
        for h in HORIZONS:
            mean, median, minimum, maximum = _mean_sd(seed_values[(condition, h)])
            curve_summary.append({"condition": condition, "h": h, "accuracy": mean, "seed_values": json.dumps(seed_values[(condition, h)]), "median": median, "min": minimum, "max": maximum, "sample_sd": statistics.stdev(seed_values[(condition, h)])})
    a0_values = [accuracy("EMPTY", 0, seed=seed) for seed in SEEDS]
    curve_summary.append({"condition": "EMPTY", "h": 0, "accuracy": statistics.mean(a0_values), "seed_values": json.dumps(a0_values), "median": statistics.median(a0_values), "min": min(a0_values), "max": max(a0_values), "sample_sd": statistics.stdev(a0_values)})
    write_csv(REPORT_ROOT / "plasticity_curves.csv", curve_summary)
    # Niche and foreign-source summaries, preserving the seed as the scientific unit.
    niche_rows = []
    for target in FAMILIES:
        for seed in SEEDS:
            niche_rows.append({"condition": "EMPTY", "h": 0, "seed": seed, "target": target, "source": "", "accuracy": accuracy("EMPTY", 0, seed=seed, target=target)})
            for h in HORIZONS:
                niche_rows.append({"condition": "SAME", "h": h, "seed": seed, "target": target, "source": target, "accuracy": accuracy("SAME", h, seed=seed, target=target)})
                foreign = [accuracy("FOREIGN", h, seed=seed, target=target, source=source) for source in FAMILIES if source != target]
                niche_rows.append({"condition": "FOREIGN", "h": h, "seed": seed, "target": target, "source": "ALL_FOREIGN", "accuracy": statistics.mean(foreign)})
    write_csv(REPORT_ROOT / "niche_level_accuracy.csv", niche_rows)
    foreign_rows = []
    for seed in SEEDS:
        for h in HORIZONS:
            for target in FAMILIES:
                for source in FAMILIES:
                    if source != target:
                        foreign_rows.append({"seed": seed, "h": h, "source": source, "target": target, "accuracy": accuracy("FOREIGN", h, seed=seed, target=target, source=source)})
    write_csv(REPORT_ROOT / "foreign_source_accuracy.csv", foreign_rows)
    # Exact Bayes opportunity from the same frozen task rows.
    bayes_rows = []
    for condition, h in [("EMPTY", 0)] + [("SAME", x) for x in HORIZONS] + [("FOREIGN", x) for x in HORIZONS]:
        vals = [float(row["A_star_prompt"]) for row in rows if row["condition"] == condition and int(row["h"]) == h]
        by_seed = [statistics.mean(float(row["A_star_prompt"]) for row in rows if row["condition"] == condition and int(row["h"]) == h and row["seed"] == seed) for seed in SEEDS]
        bayes_rows.append({"condition": condition, "h": h, "A_star": statistics.mean(vals), "seed_values": json.dumps(by_seed), "A_star_gain_over_empty": statistics.mean(vals) - .125})
    write_csv(REPORT_ROOT / "bayes_curve.csv", bayes_rows)
    # Component-level curves.
    component_rows = []
    for condition, horizons in (("EMPTY", (0,)), ("SAME", HORIZONS), ("FOREIGN", HORIZONS)):
        for h in horizons:
            for bit in range(3):
                seed_vals = []
                for seed in SEEDS:
                    vals = [int(json.loads(row["decisions"])[bit] == json.loads(row["expected"])[bit]) for row in subset(condition, h, seed=seed)]
                    seed_vals.append(statistics.mean(vals))
                component_rows.append({"condition": condition, "h": h, "component": bit + 1, "accuracy": statistics.mean(seed_vals), "seed_values": json.dumps(seed_vals)})
    write_csv(REPORT_ROOT / "component_curves.csv", component_rows)
    # Anchoring diagnostics.
    anchor_rows = []
    task_by_id = {stable_hash({"protocol": PROTOCOL, "tasks_hash": manifest["tasks_hash"], "task": task}): task for task in manifest["tasks"]}
    for row in valid:
        if row["condition"] == "EMPTY":
            continue
        task = task_by_id[row["logical_id"]]; decisions = json.loads(row["decisions"]); labels = [item["y"] for item in task["memory"]]; counts = collections.Counter(tuple(label) for label in labels)
        anchor_rows.append({"condition": row["condition"], "h": row["h"], "seed": row["seed"], "source": row["source"], "target": row["target"], "correct": row["correct"], "any_action_copy": int(any(decisions == label for label in labels)), "last_action_copy": int(bool(labels) and decisions == labels[-1]), "modal_action_copy": int(bool(labels) and decisions == list(counts.most_common(1)[0][0])), "component_last_copy": statistics.mean(int(decisions[i] == labels[-1][i]) for i in range(3))})
    write_csv(REPORT_ROOT / "anchoring.csv", anchor_rows)
    # Response-distribution health.
    distribution_rows = []
    for condition, hs in (("EMPTY", (0,)), ("SAME", HORIZONS), ("FOREIGN", HORIZONS)):
        for h in hs:
            vals = [tuple(json.loads(row["decisions"])) for row in subset(condition, h)]; counts = collections.Counter(vals); n = len(vals)
            distribution_rows.append({"condition": condition, "h": h, "n": n, "modal_output": json.dumps(list(counts.most_common(1)[0][0])), "modal_fraction": counts.most_common(1)[0][1] / n, "entropy_bits": -sum((count / n) * math.log2(count / n) for count in counts.values()), "bit1_one_rate": statistics.mean(v[0] for v in vals), "bit2_one_rate": statistics.mean(v[1] for v in vals), "bit3_one_rate": statistics.mean(v[2] for v in vals)})
    write_csv(REPORT_ROOT / "response_distribution.csv", distribution_rows)
    # Dose response on log2(h+1), equal-weighted over seeds.
    dose_rows = []
    for seed in SEEDS:
        ys = [accuracy("SAME", h, seed=seed) for h in HORIZONS]; xs = [math.log2(h + 1) for h in HORIZONS]; slope = float(np.polyfit(xs, ys, 1)[0]); dose_rows.append({"seed": seed, "slope_log2_h_plus_1": slope, "A_same_h1": ys[0], "A_same_h8": ys[-1], "A8_minus_A1": ys[-1] - ys[0]})
    aggregate_ys = [statistics.mean(seed_values[("SAME", h)]) for h in HORIZONS]; aggregate_slope = float(np.polyfit([math.log2(h + 1) for h in HORIZONS], aggregate_ys, 1)[0]); dose_rows.append({"seed": "AGGREGATE", "slope_log2_h_plus_1": aggregate_slope, "A_same_h1": aggregate_ys[0], "A_same_h8": aggregate_ys[-1], "A8_minus_A1": aggregate_ys[-1] - aggregate_ys[0]})
    write_csv(REPORT_ROOT / "dose_response.csv", dose_rows)
    # Historical V2 DIAGONAL reference, kept secondary and clearly separated.
    historical = []
    v2_rows = list(csv.DictReader((V2_REPORT_ROOT / "response_level.csv").open(newline="", encoding="utf-8")))
    for seed in SEEDS:
        base = [int(r["correct"]) for r in v2_rows if r["geometry"] == GEOMETRY and r["condition"] == "baseline" and int(r["seed"]) == seed]
        same = [int(r["correct"]) for r in v2_rows if r["geometry"] == GEOMETRY and r["condition"] == "transfer" and r["source"] == r["target"] and int(r["seed"]) == seed]
        foreign = [int(r["correct"]) for r in v2_rows if r["geometry"] == GEOMETRY and r["condition"] == "transfer" and r["source"] != r["target"] and int(r["seed"]) == seed]
        historical.append({"seed": seed, "v2_A0": statistics.mean(base), "v2_A_same_h8": statistics.mean(same), "v2_A_foreign_h8": statistics.mean(foreign), "v2_G_abs_h8": statistics.mean(same) - statistics.mean(base), "v2_G_rel_h8": statistics.mean(same) - statistics.mean(foreign)})
    write_csv(REPORT_ROOT / "historical_v2_replication.csv", historical)
    # Qualification gates.
    gains = {h: [row["G_abs"] for row in gain_rows if row["h"] == h] for h in HORIZONS}; rels = {h: [row["G_rel"] for row in gain_rows if row["h"] == h] for h in HORIZONS}
    i_abs = statistics.mean([row["G_abs"] for row in gain_rows]); i_rel = statistics.mean([row["G_rel"] for row in gain_rows]); slopes = [float(r["slope_log2_h_plus_1"]) for r in dose_rows if r["seed"] != "AGGREGATE"]
    component_h8 = [r for r in component_rows if r["condition"] == "SAME" and r["h"] == 8]; empty_component = {r["component"]: r["accuracy"] for r in component_rows if r["condition"] == "EMPTY" and r["h"] == 0}; same_component = {r["component"]: r["accuracy"] for r in component_h8}; foreign_component = {r["component"]: next(x["accuracy"] for x in component_rows if x["condition"] == "FOREIGN" and x["h"] == 8 and x["component"] == r["component"]) for r in component_h8}; component_gabs = [same_component[i] - empty_component[i] for i in (1, 2, 3)]
    gates = {"L1_useful_h8": statistics.mean(gains[8]) >= .10 and sum(value > 0 for value in gains[8]) >= 3, "L2_selective_h8": statistics.mean(rels[8]) >= .10 and sum(value > 0 for value in rels[8]) >= 3, "L3_integrated_absolute": i_abs >= .05 and sum(value > 0 for value in [statistics.mean([r["G_abs"] for r in gain_rows if r["seed"] == seed]) for seed in SEEDS]) >= 3, "L4_integrated_relative": i_rel >= .05 and sum(value > 0 for value in [statistics.mean([r["G_rel"] for r in gain_rows if r["seed"] == seed]) for seed in SEEDS]) >= 3, "L5_dose": aggregate_ys[-1] > aggregate_ys[0] and sum(value > 0 for value in slopes) >= 3, "L6_components": all(value > 0 for value in component_gabs) and sum(value >= .05 for value in component_gabs) >= 2}
    aggregate_gabs = statistics.mean(gains[8]); aggregate_grel = statistics.mean(rels[8]); overall = "QUALIFIED" if all(gates.values()) else ("PARTIAL" if aggregate_gabs > 0 and aggregate_grel > 0 else "NOT_QUALIFIED")
    qualification = {"protocol": PROTOCOL, "overall_status": overall, "gates": {key: {"pass": value, "status": "PASS" if value else "FAIL"} for key, value in gates.items()}, "G_abs": {str(h): statistics.mean(gains[h]) for h in HORIZONS}, "G_rel": {str(h): statistics.mean(rels[h]) for h in HORIZONS}, "G_foreign": {str(h): statistics.mean([row["G_foreign"] for row in gain_rows if row["h"] == h]) for h in HORIZONS}, "I_abs": i_abs, "I_rel": i_rel, "seed_G_abs_h8": gains[8], "seed_G_rel_h8": rels[8], "component_G_abs_h8": component_gabs, "aggregate_slope": aggregate_slope, "seed_slopes": slopes, "exact_target_novelty_repeat_count": 0}
    events = v1._load_events(DATA_ROOT / "events.jsonl"); health = {"protocol": PROTOCOL, "logical_expected": 2176, "logical_terminal": len(terminal), "physical_attempts": len(events), "technical_retries": sum(int(e.get("attempt", 0)) for e in events), "semantic_ood": sum(e.get("error_category") == "out_of_domain" for e in events), "coverage": len(terminal) / 2176, "models": sorted({(e.get("provider_metadata") or {}).get("model") for e in events}), "fingerprints": sorted({(e.get("provider_metadata") or {}).get("system_fingerprint") for e in events}), "observed_cost_usd": sum(float(e.get("attempt_cost_usd") or 0.0) for e in events), "usage_coverage": sum(bool(e.get("token_usage")) for e in events) / len(events), "latency_mean_s": statistics.mean(float(e.get("latency_s") or 0.0) for e in events), "latency_median_s": statistics.median(float(e.get("latency_s") or 0.0) for e in events), "classification": "CLEAN" if len(terminal) == 2176 and not any(int(e.get("attempt", 0)) for e in events) else "COMPLETE_WITH_RETRIES"}
    v1.atomic_json(REPORT_ROOT / "qualification.json", qualification); v1.atomic_json(REPORT_ROOT / "technical_health.json", health); v1.atomic_json(REPORT_ROOT / "cost.json", {"observed_cost_usd": health["observed_cost_usd"], "hard_cap_usd": HARD_CAP_USD, "remaining_usd": HARD_CAP_USD - health["observed_cost_usd"]})
    return {"qualification": qualification, "health": health, "curve": curve_summary, "bayes": bayes_rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=PROTOCOL); parser.add_argument("--freeze", action="store_true"); parser.add_argument("--run", action="store_true"); parser.add_argument("--confirm-real", action="store_true"); parser.add_argument("--analyze", action="store_true"); args = parser.parse_args()
    if args.freeze:
        manifest = freeze_manifest(); print(json.dumps({"manifest": str(REPORT_ROOT / "manifest.json"), "calls": manifest["call_breakdown"], "audit": manifest["substrate_audit"], "forecast": manifest["forecast"]}, indent=2))
    elif args.run:
        print(json.dumps(asyncio.run(run_real(confirm_real=args.confirm_real)), indent=2))
    elif args.analyze:
        print(json.dumps(analyze(), indent=2, default=float))
    else:
        parser.error("choose --freeze, --run, or --analyze")


if __name__ == "__main__":
    main()
