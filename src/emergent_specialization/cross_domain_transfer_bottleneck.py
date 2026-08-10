"""Frozen cross-domain transfer bottleneck diagnostic.

This is a single-agent calibration ladder, not a society experiment.  It reuses
the V2 histories/probes exactly and supplies progressively more privileged
structure: relation only, semantic correspondence, canonical representation,
explicit rule with semantic target, and explicit rule with canonical target.
The module is offline-safe unless ``--run --confirm-real`` is supplied.
"""

from __future__ import annotations

import argparse
import collections
import csv
import fcntl
import itertools
import json
import math
import random
import statistics
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from . import observable_learner_calibration_v2 as v2
from . import relation_signal_causal_transfer as relation
from .ecological_information import FAMILIES, GEOMETRIES, V3Case, generate_environment, solve
from .ecological_information_v31 import SEMANTIC_SCHEMAS
from .credentials import CredentialStore
from .models import BackendResponse
from .providers import DeepSeekDirectBackend

ROOT = Path(__file__).resolve().parents[2]
V2_REPORT_ROOT = ROOT / "reports/task-ecology/observable-learner-calibration-v2"
V2_DATA_ROOT = ROOT / "data/auto-research/observable-learner-calibration-v2"
RELATION_DATA_ROOT = ROOT / "data/auto-research/relation-signal-causal-transfer-v1"
REPORT_ROOT = ROOT / "reports/task-ecology/cross-domain-transfer-bottleneck-v1"
DATA_ROOT = ROOT / "data/auto-research/cross-domain-transfer-bottleneck-v1"
PROTOCOL = "CROSS-DOMAIN-TRANSFER-BOTTLENECK-V1"
MODEL = "deepseek-v4-flash"
SEEDS = (9201, 9202, 9203, 9204)
H = 8
ARMS = ("LOCAL_REP", "A0_RELATION_ONLY", "A1_SEMANTIC_PI", "A2_CANONICAL", "A3_RULE_SEMANTIC", "A4_RULE_CANONICAL")
CROSS_ARMS = ARMS[1:]
EXECUTION_ORDER_SEED = 20260811
MAX_ATTEMPTS = 2
HARD_CAP_USD = 0.15
RESERVATION_USD = 0.00015
INPUT_PRICE = 0.14
CACHED_INPUT_PRICE = 0.0028
OUTPUT_PRICE = 0.28
SYSTEM_PROMPT = v2.SYSTEM_PROMPT
OUTPUT_INSTRUCTION = v2.OUTPUT_INSTRUCTION
STATIC_INSTRUCTION_HASH = v2.stable_hash([SYSTEM_PROMPT, OUTPUT_INSTRUCTION])
R_NONE = "Policy relationship: the relation between the previous resolved cases and the current case is not specified."
PI_INTRO = "The following is an explicit correspondence between the source and target semantic attributes for this comparison."
RETRYABLE = {"parse_error", "empty_content", "transient_transport", "transport", "rate_limit", "server_error", "overloaded"}


def now() -> str:
    return datetime.now(UTC).isoformat()


def stable_hash(value: Any) -> str:
    return v2.stable_hash(value)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def relation_for(geometry: str, source: str, target: str) -> str:
    return relation.relation_for(geometry, source, target)


def source_identifiability(task: dict[str, Any]) -> dict[str, Any]:
    return relation._source_policy_metadata(task)


def _semantic_case(record: dict[str, Any]) -> str:
    return v2._render(record)


def _canonical_case(record: dict[str, Any]) -> str:
    x = record["x"]
    return "Canonical case: dimension 1 state {}; dimension 2 state {}; dimension 3 state {}.".format(*x)


def _history_block(task: dict[str, Any], *, canonical: bool) -> str:
    lines = []
    for item in task["memory"]:
        case = _canonical_case(item) if canonical else _semantic_case(item)
        lines.append(case + f"\nResolved decision: {json.dumps(item['y'], separators=(',', ':'))}")
    return "Prior resolved cases:\n" + "\n\n".join(lines)


def _target_block(task: dict[str, Any], *, canonical: bool) -> str:
    case = _canonical_case(task["probe"]) if canonical else _semantic_case(task["probe"])
    return "CURRENT CASE:\n" + case


def _pi_block(source: str, target: str) -> str:
    s = SEMANTIC_SCHEMAS[source]; t = SEMANTIC_SCHEMAS[target]
    lines = [PI_INTRO]
    for index, ((sn, sv), (tn, tv)) in enumerate(zip(s["attributes"], t["attributes"]), 1):
        lines.append(f"Attribute {index}: {sn} <-> {tn}")
        for left, right in zip(sv, tv): lines.append(f"  {left} <-> {right}")
    lines.append("The first source decision corresponds to the first target decision, and likewise for the second and third decisions.")
    lines.append("The same hidden policy applies after these correspondences are used.")
    return "\n".join(lines)


def _rule_block(task: dict[str, Any], *, canonical: bool) -> str:
    env = generate_environment(task["geometry"], int(task["seed"]))
    # True source/target policy is safe host metadata; it is never emitted as a
    # family ID or theta index.  A3 renders values in the target schema; A4
    # renders the same table in canonical states.
    schema = SEMANTIC_SCHEMAS[task["target"]]
    lines = ["The supplied policy tables apply to the current case. Use them directly; do not infer a different rule."]
    for j, mapping in enumerate(env.theta_by_family[task["source"]], 1):
        lines.append(f"Policy dimension {j}:")
        for state, bit in enumerate(mapping):
            label = f"state {state}" if canonical else schema["attributes"][j - 1][1][state]
            lines.append(f"  {label} -> decision bit {bit}")
    return "\n".join(lines)


def render_user(task: dict[str, Any]) -> str:
    arm = task["arm"]
    if arm == "LOCAL_REP":
        body = [_history_block(task, canonical=False), _target_block(task, canonical=False)]
    elif arm == "A0_RELATION_ONLY":
        body = [relation.CUE_STRINGS["RS"], _history_block(task, canonical=False), _target_block(task, canonical=False)]
    elif arm == "A1_SEMANTIC_PI":
        body = [relation.CUE_STRINGS["RS"], _pi_block(task["source"], task["target"]), _history_block(task, canonical=False), _target_block(task, canonical=False)]
    elif arm == "A2_CANONICAL":
        body = [relation.CUE_STRINGS["RS"], "The source and target are represented by the same three canonical policy dimensions.", _history_block(task, canonical=True), _target_block(task, canonical=True)]
    elif arm == "A3_RULE_SEMANTIC":
        body = [_rule_block(task, canonical=False), _target_block(task, canonical=False)]
    elif arm == "A4_RULE_CANONICAL":
        body = [_rule_block(task, canonical=True), _target_block(task, canonical=True)]
    else:
        raise ValueError(arm)
    body.append(OUTPUT_INSTRUCTION)
    return "\n\n".join(body)


def _has_answer_leak(task: dict[str, Any]) -> bool:
    """Reject explicit answer-vector strings, while permitting rule tables."""
    text = render_user(task)
    truth = json.dumps(task["probe"]["y"], separators=(",", ":"))
    forbidden = (f'"decisions":{truth}', f"decisions = {truth}", f"answer: {truth}", f"answer = {truth}")
    return any(token in text for token in forbidden)


def _base_tasks() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    manifest = json.loads((V2_REPORT_ROOT / "manifest.json").read_text(encoding="utf-8"))
    tasks = manifest["tasks"]
    local = [task for task in tasks if task["condition"] == "transfer" and task["source"] == task["target"]]
    cross_same = [task for task in tasks if task["condition"] == "transfer" and task["source"] != task["target"] and relation_for(task["geometry"], task["source"], task["target"]) == "SAME_POLICY"]
    return local, cross_same


def build_tasks() -> list[dict[str, Any]]:
    local, cross = _base_tasks(); tasks: list[dict[str, Any]] = []
    for base, arms in [(task, ("LOCAL_REP",)) for task in local] + [(task, CROSS_ARMS) for task in cross]:
        metadata = source_identifiability(base)
        base_id = stable_hash({"protocol": v2.PROTOCOL, "tasks_hash": json.loads((V2_REPORT_ROOT / "manifest.json").read_text())["tasks_hash"], "task": base})
        for arm in arms:
            task = json.loads(json.dumps(base)); task.update({"protocol": PROTOCOL, "arm": arm, "underlying_task_id": base_id, "actual_relation": relation_for(base["geometry"], base["source"], base["target"]), **metadata})
            task["pi_id"] = stable_hash({"source": base["source"], "target": base["target"]}) if arm == "A1_SEMANTIC_PI" else None
            task["explicit_rule"] = arm in {"A3_RULE_SEMANTIC", "A4_RULE_CANONICAL"}
            task["representation_mode"] = {"LOCAL_REP": "semantic", "A0_RELATION_ONLY": "semantic", "A1_SEMANTIC_PI": "semantic_pi", "A2_CANONICAL": "canonical", "A3_RULE_SEMANTIC": "rule_semantic", "A4_RULE_CANONICAL": "rule_canonical"}[arm]
            task["prompt_hash"] = stable_hash({"system": SYSTEM_PROMPT, "user": render_user(task)})
            task["static_instruction_hash"] = STATIC_INSTRUCTION_HASH
            task["answer_leak"] = _has_answer_leak(task)
            tasks.append(task)
    # Interleave all conditions within each seed/geometry/source/target/probe
    # stratum, then use a frozen seed for physical ordering.
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = collections.defaultdict(list)
    for task in tasks:
        groups[(task["seed"], task["geometry"], task["source"], task["target"], task["probe"]["case_id"])].append(task)
    rng = random.Random(EXECUTION_ORDER_SEED); group_values = list(groups.values()); rng.shuffle(group_values)
    ordered: list[dict[str, Any]] = []
    for group in group_values:
        group.sort(key=lambda t: ARMS.index(t["arm"]))
        rng.shuffle(group)
        for task in group:
            task["execution_order"] = len(ordered); ordered.append(task)
    return ordered


def expected_calls() -> dict[str, int]:
    return {"local": 384, "cross_per_arm": 512, "cross_arms": 5, "cross_total": 2560, "total": 2944}


def _recent_forecast(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    events = relation.v2.v1._load_events(RELATION_DATA_ROOT / "events.jsonl")
    old_tasks = relation.build_tasks()
    old_chars = [len(relation.SYSTEM_PROMPT) + len(relation.render_user(t, t["arm"])) for t in old_tasks]
    new_chars = [len(SYSTEM_PROMPT) + len(render_user(t)) for t in tasks]
    costs = [float(e["attempt_cost_usd"]) for e in events if e.get("attempt_cost_usd") is not None]
    mean_cost = statistics.mean(costs) if costs else 0.0
    old_mean_chars = statistics.mean(old_chars); new_mean_chars = statistics.mean(new_chars)
    projected = mean_cost * len(tasks) * new_mean_chars / old_mean_chars
    return {"logical_calls": len(tasks), "relation_mean_cost_usd": mean_cost, "old_mean_prompt_chars": old_mean_chars, "new_mean_prompt_chars": new_mean_chars, "min_prompt_chars": min(new_chars), "max_prompt_chars": max(new_chars), "projected_cost_usd": projected, "safety_margin_50pct_usd": projected * 1.5, "hard_cap_usd": HARD_CAP_USD, "within_cap_with_margin": projected * 1.5 <= HARD_CAP_USD}


def freeze_manifest() -> dict[str, Any]:
    tasks = build_tasks(); expected = expected_calls()
    if len(tasks) != expected["total"]: raise RuntimeError(f"call count mismatch {len(tasks)}")
    counts = collections.Counter(task["arm"] for task in tasks)
    if counts["LOCAL_REP"] != expected["local"] or any(counts[arm] != expected["cross_per_arm"] for arm in CROSS_ARMS): raise RuntimeError(f"arm count mismatch {counts}")
    if any(task["answer_leak"] for task in tasks): raise RuntimeError("explicit target answer leakage")
    unique = {}
    for task in tasks: unique.setdefault(task["underlying_task_id"], task)
    ident = sum(float(t["A_star_source"]) >= .99 for t in unique.values())
    if ident / len(unique) < .90: raise RuntimeError(f"source identifiability failed {ident}/{len(unique)}")
    forecast = _recent_forecast(tasks)
    if not forecast["within_cap_with_margin"]: raise RuntimeError(f"cost forecast exceeds cap: {forecast}")
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    write_csv(REPORT_ROOT / "pi_correspondence.csv", [{"source": s, "target": t, "pi_id": stable_hash({"source": s, "target": t}), "attribute_pairs": json.dumps([[a[0], b[0]] for a, b in zip(SEMANTIC_SCHEMAS[s]["attributes"], SEMANTIC_SCHEMAS[t]["attributes"])])} for s in FAMILIES for t in FAMILIES if s != t])
    manifest = {"protocol": PROTOCOL, "created_at_utc": now(), "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "provider": "deepseek_direct", "model": MODEL, "thinking": "off", "seeds": list(SEEDS), "geometries": list(GEOMETRIES), "families": list(FAMILIES), "h": H, "arms": list(ARMS), "cross_arms": list(CROSS_ARMS), "execution_order_seed": EXECUTION_ORDER_SEED, "logical_calls": expected["total"], "call_breakdown": expected, "source_identifiability_count": ident, "source_identifiability_fraction": ident / len(unique), "hard_cap_usd": HARD_CAP_USD, "forecast": forecast, "tasks": tasks}
    manifest["tasks_hash"] = stable_hash(tasks); path = REPORT_ROOT / "manifest.json"
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        if old.get("tasks_hash") != manifest["tasks_hash"]: raise RuntimeError("existing bottleneck manifest differs")
        return old
    v2.atomic_json(path, manifest); return manifest


def _budget_change(*, reserve: float = 0.0, release: float = 0.0, actual: float = 0.0) -> dict[str, Any]:
    path = DATA_ROOT / "campaign_budget.json"; lock_path = path.with_suffix(".lock"); path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        budget = json.loads(path.read_text()) if path.exists() else {"protocol": PROTOCOL, "hard_cap_usd": HARD_CAP_USD, "spent_usd": 0.0, "reserved_usd": 0.0}
        spent, held = float(budget.get("spent_usd", 0.0)), float(budget.get("reserved_usd", 0.0))
        if held + 1e-12 < release or spent + held - release + reserve + actual > HARD_CAP_USD + 1e-12: raise RuntimeError("bottleneck hard budget guard")
        budget.update(spent_usd=spent + actual, reserved_usd=held - release + reserve, updated_at_utc=now()); v2.atomic_json(path, budget); return budget


def _append(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle: handle.write(json.dumps(event, sort_keys=True) + "\n"); handle.flush()


def _cost(response: BackendResponse) -> float | None:
    from .costs import estimate_usage_cost
    return estimate_usage_cost(response.token_usage, input_per_million_tokens=INPUT_PRICE, cached_input_per_million_tokens=CACHED_INPUT_PRICE, output_per_million_tokens=OUTPUT_PRICE)


async def run_real(*, confirm_real: bool = False) -> dict[str, Any]:
    if not confirm_real: raise SystemExit("bottleneck diagnostic requires --confirm-real")
    manifest = json.loads((REPORT_ROOT / "manifest.json").read_text(encoding="utf-8")); events_path = DATA_ROOT / "events.jsonl"; status_path = DATA_ROOT / "run_status.json"
    if manifest.get("logical_calls") != 2944 or manifest.get("tasks_hash") != stable_hash(manifest["tasks"]): raise RuntimeError("bottleneck manifest integrity failure")
    events = v2.v1._load_events(events_path); done = {e["logical_id"] for e in events if e.get("terminal")}; attempts = collections.defaultdict(int)
    for event in events: attempts[event["logical_id"]] = max(attempts[event["logical_id"]], int(event.get("attempt", 0)) + 1)
    status = json.loads(status_path.read_text()) if status_path.exists() else {"protocol": PROTOCOL, "status": "initialized", "tasks_hash": manifest["tasks_hash"], "logical_calls": 2944, "created_at_utc": now()}
    if status.get("tasks_hash") != manifest["tasks_hash"]: raise RuntimeError("status/manifest mismatch")
    status.update(status="running", started_or_resumed_at_utc=now()); v2.atomic_json(status_path, status)
    backend = None; spent = sum(float(e.get("attempt_cost_usd") or 0) for e in events); retries = sum(int(e.get("attempt", 0)) for e in events)
    try:
        key = CredentialStore().get(source="keychain"); backend = DeepSeekDirectBackend(api_key=key, thinking="off", max_tokens=32)
        for task in manifest["tasks"]:
            lid = stable_hash({"protocol": PROTOCOL, "tasks_hash": manifest["tasks_hash"], "task": task})
            if lid in done: continue
            start = attempts.get(lid, 0)
            if start >= MAX_ATTEMPTS: raise RuntimeError(f"retry exhaustion {lid}")
            for attempt in range(start, MAX_ATTEMPTS):
                _budget_change(reserve=RESERVATION_USD)
                try:
                    response = await backend.complete(system_prompt=SYSTEM_PROMPT, user_prompt=render_user(task), model=MODEL, model_parameters={"thinking": "off", "max_tokens": 32})
                    cost = _cost(response)
                except Exception:
                    _budget_change(release=RESERVATION_USD); raise
                if cost is None: _budget_change(release=RESERVATION_USD); raise RuntimeError("usage/cost unavailable")
                _budget_change(release=RESERVATION_USD, actual=cost); spent += cost
                decisions, parse_category = v2.v1.parse_decisions(response.raw_response); provider = response.provider_metadata or {}; category = response.error_category or parse_category; error = response.error or parse_category
                if provider.get("model") != MODEL: raise RuntimeError(f"model mismatch {provider.get('model')!r}")
                terminal = category == "out_of_domain" or (error is None and decisions is not None)
                event = {"protocol": PROTOCOL, "logical_id": lid, "attempt": attempt, "task": task, "decisions": decisions, "expected": task["probe"]["y"], "correct": decisions == task["probe"]["y"] if decisions is not None else False, "source_policy_correct": decisions == task["source_policy_action"] if decisions is not None else False, "error": error, "error_category": category, "terminal": terminal, "raw_model_response": response.raw_response, "latency_s": response.latency_s, "token_usage": response.token_usage, "provider_metadata": provider, "attempt_cost_usd": cost, "finished_at_utc": now()}
                _append(events_path, event); events.append(event)
                if terminal: done.add(lid); break
                if not response.retryable or category not in RETRYABLE: raise RuntimeError(f"non-retryable response {category}")
                retries += 1
            else: raise RuntimeError(f"retry exhaustion {lid}")
        if len(done) != 2944: raise RuntimeError(f"coverage {len(done)}/2944")
        status.update(status="completed", physical_attempts=len(events), retries=retries, observed_cost_usd=spent, finished_at_utc=now())
    except Exception as exc:
        status.update(status="incomplete", failure=f"{type(exc).__name__}: {exc}", physical_attempts=len(events), retries=retries, observed_cost_usd=spent, finished_at_utc=now())
    finally:
        if backend is not None: await backend.close()
        v2.atomic_json(status_path, status)
    return status


def _load_terminal(manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    events = v2.v1._load_events(DATA_ROOT / "events.jsonl"); grouped: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for event in events: grouped[event["logical_id"]].append(event)
    terminal = {}
    rows = []
    for task in manifest["tasks"]:
        lid = stable_hash({"protocol": PROTOCOL, "tasks_hash": manifest["tasks_hash"], "task": task}); values = [e for e in grouped.get(lid, []) if e.get("terminal")]
        if values: terminal[lid] = values[-1]
    if len(terminal) != manifest["logical_calls"]: raise RuntimeError(f"coverage {len(terminal)}/{manifest['logical_calls']}")
    for task in manifest["tasks"]:
        lid = stable_hash({"protocol": PROTOCOL, "tasks_hash": manifest["tasks_hash"], "task": task}); event = terminal[lid]; decisions = event.get("decisions"); target = task["probe"]["y"]
        rows.append({"arm": task["arm"], "geometry": task["geometry"], "seed": task["seed"], "source": task["source"], "target": task["target"], "probe_id": task["probe"]["case_id"], "underlying_task_id": task["underlying_task_id"], "decisions": json.dumps(decisions, separators=(",", ":")) if decisions is not None else "", "target_truth": json.dumps(target, separators=(",", ":")), "correct": int(decisions == target) if decisions is not None else 0, "source_policy_correct": int(decisions == task["source_policy_action"]) if decisions is not None else 0, "valid": int(decisions is not None), "A_star_source": task["A_star_source"], "source_policy_action": json.dumps(task["source_policy_action"], separators=(",", ":")), "error_category": event.get("error_category") or "", "latency_s": event.get("latency_s"), "attempt_cost_usd": event.get("attempt_cost_usd"), "token_usage": json.dumps(event.get("token_usage") or {}), "model": (event.get("provider_metadata") or {}).get("model", "")})
    return rows, terminal


def analyze() -> dict[str, Any]:
    manifest = json.loads((REPORT_ROOT / "manifest.json").read_text(encoding="utf-8")); rows, terminal = _load_terminal(manifest); write_csv(REPORT_ROOT / "response_level.csv", rows)
    def valid(arm: str) -> list[dict[str, Any]]: return [r for r in rows if r["arm"] == arm and r["valid"]]
    def acc(arm: str, seed: int | None = None) -> float:
        values = [r["correct"] for r in valid(arm) if seed is None or int(r["seed"]) == seed]; return statistics.mean(values) if values else float("nan")
    ladder = [{"condition": arm, "n": len([r for r in rows if r["arm"] == arm]), "valid_n": len(valid(arm)), "joint_accuracy": acc(arm), "bit1_accuracy": statistics.mean(json.loads(r["decisions"])[0] == json.loads(r["target_truth"])[0] for r in valid(arm)) if valid(arm) else float("nan"), "bit2_accuracy": statistics.mean(json.loads(r["decisions"])[1] == json.loads(r["target_truth"])[1] for r in valid(arm)) if valid(arm) else float("nan"), "bit3_accuracy": statistics.mean(json.loads(r["decisions"])[2] == json.loads(r["target_truth"])[2] for r in valid(arm)) if valid(arm) else float("nan")} for arm in ARMS]
    write_csv(REPORT_ROOT / "ladder_summary.csv", ladder)
    local_map = {(r["geometry"], int(r["seed"]), r["source"], r["probe_id"]): r for r in valid("LOCAL_REP")}
    transport = []; strata = []
    for arm in ("A0_RELATION_ONLY", "A1_SEMANTIC_PI", "A2_CANONICAL"):
        cross = valid(arm)
        for r in cross:
            key = (r["geometry"], int(r["seed"]), r["source"], r["probe_id"]); local = local_map[key]
            local_decisions = json.loads(local["decisions"]); cross_decisions = json.loads(r["decisions"])
            transport.append({"arm": arm, "seed": r["seed"], "source": r["source"], "target": r["target"], "probe_id": r["probe_id"], "local_correct": local["correct"], "cross_correct": r["correct"], "matches_local_response": int(cross_decisions == local_decisions)})
    write_csv(REPORT_ROOT / "model_source_transport.csv", transport)
    for arm in ("A0_RELATION_ONLY", "A1_SEMANTIC_PI", "A2_CANONICAL"):
        for local_ok in (0, 1):
            subset = [r for r in transport if r["arm"] == arm and r["local_correct"] == local_ok]; strata.append({"arm": arm, "local_correct": local_ok, "n": len(subset), "cross_accuracy": statistics.mean(r["cross_correct"] for r in subset) if subset else float("nan"), "transport_rate": statistics.mean(r["matches_local_response"] for r in subset) if subset else float("nan")})
    write_csv(REPORT_ROOT / "source_success_stratification.csv", strata)
    seed_rows = []
    for seed in SEEDS:
        seed_rows.append({"seed": seed, **{arm: acc(arm, seed) for arm in ARMS}, "Delta_Pi": acc("A1_SEMANTIC_PI", seed) - acc("A0_RELATION_ONLY", seed), "A2_minus_A1": acc("A2_CANONICAL", seed) - acc("A1_SEMANTIC_PI", seed), "A4_minus_A2": acc("A4_RULE_CANONICAL", seed) - acc("A2_CANONICAL", seed), "A4_minus_A3": acc("A4_RULE_CANONICAL", seed) - acc("A3_RULE_SEMANTIC", seed)})
    write_csv(REPORT_ROOT / "seed_level_contrasts.csv", seed_rows)
    comp_rows = []
    for arm in ARMS:
        for bit in range(3):
            subset = valid(arm); comp_rows.append({"condition": arm, "component": bit + 1, "n": len(subset), "accuracy": statistics.mean(json.loads(r["decisions"])[bit] == json.loads(r["target_truth"])[bit] for r in subset) if subset else float("nan")})
    write_csv(REPORT_ROOT / "component_metrics.csv", comp_rows)
    pair_rows = []
    for arm in CROSS_ARMS:
        for source in FAMILIES:
            for target in FAMILIES:
                subset = [r for r in valid(arm) if r["source"] == source and r["target"] == target]; pair_rows.append({"condition": arm, "source": source, "target": target, "n": len(subset), "accuracy": statistics.mean(r["correct"] for r in subset) if subset else float("nan")})
    write_csv(REPORT_ROOT / "semantic_pair_metrics.csv", pair_rows)
    anchoring = []
    manifest_tasks = {(task["arm"], task["underlying_task_id"]): task for task in manifest["tasks"]}
    for r in valid("A0_RELATION_ONLY") + valid("A1_SEMANTIC_PI") + valid("A2_CANONICAL"):
        task = manifest_tasks[(r["arm"], r["underlying_task_id"])]
        decisions = json.loads(r["decisions"]); labels = [item["y"] for item in task["memory"]]; counts = collections.Counter(tuple(label) for label in labels)
        anchoring.append({"condition": r["arm"], "any_action_copy": int(any(decisions == label for label in labels)), "last_action_copy": int(bool(labels) and decisions == labels[-1]), "modal_action_copy": int(bool(labels) and decisions == list(counts.most_common(1)[0][0])), "correct": r["correct"], "source_policy_correct": r["source_policy_correct"]})
    write_csv(REPORT_ROOT / "anchoring.csv", anchoring)
    distributions = []
    for arm in ARMS:
        subset = valid(arm); values = [tuple(json.loads(r["decisions"])) for r in subset]; counts = collections.Counter(values); distributions.append({"condition": arm, "n": len(values), "modal_output": json.dumps(list(counts.most_common(1)[0][0])) if values else "", "modal_fraction": counts.most_common(1)[0][1] / len(values) if values else float("nan"), "entropy_bits": -sum(n / len(values) * math.log2(n / len(values)) for n in counts.values()) if values else float("nan")})
    write_csv(REPORT_ROOT / "response_distribution.csv", distributions)
    events = v2.v1._load_events(DATA_ROOT / "events.jsonl"); health = {"protocol": PROTOCOL, "logical_expected": 2944, "logical_terminal": len(terminal), "physical_attempts": len(events), "technical_retries": sum(int(e.get("attempt", 0)) for e in events), "semantic_ood": sum(e.get("error_category") == "out_of_domain" for e in events), "coverage": len(terminal) / 2944, "models": sorted({(e.get("provider_metadata") or {}).get("model") for e in events}), "observed_cost_usd": sum(float(e.get("attempt_cost_usd") or 0) for e in events), "usage_coverage": sum(bool(e.get("token_usage")) for e in events) / len(events), "classification": "CLEAN" if len(terminal) == 2944 and not any(int(e.get("attempt", 0)) for e in events) else "COMPLETE_WITH_RETRIES"}
    v2.atomic_json(REPORT_ROOT / "technical_health.json", health); v2.atomic_json(REPORT_ROOT / "cost.json", {"observed_cost_usd": health["observed_cost_usd"], "hard_cap_usd": HARD_CAP_USD, "remaining_usd": HARD_CAP_USD - health["observed_cost_usd"]})
    summary = {"protocol": PROTOCOL, "logical_calls": 2944, "health": health, "ladder": ladder, "seed_level": seed_rows, "gaps": {"Gap_cross": acc("LOCAL_REP") - acc("A0_RELATION_ONLY"), "Delta_Pi": acc("A1_SEMANTIC_PI") - acc("A0_RELATION_ONLY"), "Delta_canonical": acc("A2_CANONICAL") - acc("A1_SEMANTIC_PI"), "Gap_induction_canonical": acc("A4_RULE_CANONICAL") - acc("A2_CANONICAL"), "Gap_target_semantics": acc("A4_RULE_CANONICAL") - acc("A3_RULE_SEMANTIC")}, "qualification": {"count": 2944, "model": MODEL, "answer_leak": any(bool(t["answer_leak"]) for t in manifest["tasks"]), "source_identifiability_fraction": manifest["source_identifiability_fraction"]}}
    v2.atomic_json(REPORT_ROOT / "qualification.json", summary["qualification"]); v2.atomic_json(REPORT_ROOT / "analysis_summary.json", summary); return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=PROTOCOL); parser.add_argument("--freeze", action="store_true"); parser.add_argument("--run", action="store_true"); parser.add_argument("--confirm-real", action="store_true"); parser.add_argument("--analyze", action="store_true"); args = parser.parse_args()
    if args.freeze: print(json.dumps((lambda m: {"manifest": str(REPORT_ROOT / "manifest.json"), "calls": m["call_breakdown"], "source_identifiability": [m["source_identifiability_count"], m["source_identifiability_fraction"]], "forecast": m["forecast"]})(freeze_manifest()), indent=2))
    elif args.run:
        import asyncio; print(json.dumps(asyncio.run(run_real(confirm_real=args.confirm_real)), indent=2))
    elif args.analyze: print(json.dumps(analyze(), indent=2, default=float))
    else: parser.error("choose --freeze, --run, or --analyze")


if __name__ == "__main__":
    main()
