"""Frozen relation-signal causal transfer intervention.

The module reuses the completed V2 task ecology exactly and changes only one
learner-visible sentence on cross-domain prompts.  Manifest generation,
execution, and analysis are journaled and offline-safe unless ``--run
--confirm-real`` is explicitly supplied.  No society or routing code is used.
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

from emergent_specialization.studies.ecology import regime_observability as regime
from emergent_specialization.studies.calibration import observable_learner_v2 as v2
from emergent_specialization.studies.ecology.ecological_information import FAMILIES, GEOMETRIES, V3Case, generate_environment, posterior_predictive, solve
from emergent_specialization.core.models import BackendResponse
from emergent_specialization.providers.credentials import CredentialStore
from emergent_specialization.providers import DeepSeekDirectBackend

ROOT = Path(__file__).resolve().parents[4]
V2_REPORT_ROOT = ROOT / "reports/task-ecology/observable-learner-calibration-v2"
V2_DATA_ROOT = ROOT / "data/auto-research/observable-learner-calibration-v2"
REPORT_ROOT = ROOT / "reports/task-ecology/relation-signal-causal-transfer-v1"
DATA_ROOT = ROOT / "data/auto-research/relation-signal-causal-transfer-v1"
PROTOCOL = "RELATION-SIGNAL-CAUSAL-TRANSFER-V1"
MODEL = "deepseek-v4-flash"
SEEDS = (9201, 9202, 9203, 9204)
ARMS = ("R0", "RS", "RI")
H = 8
EXECUTION_ORDER_SEED = 20260810
MAX_ATTEMPTS = 2
HARD_CAP_USD = 0.15
RESERVATION_USD = 0.00015
INPUT_PRICE = 0.14
CACHED_INPUT_PRICE = 0.0028
OUTPUT_PRICE = 0.28
SYSTEM_PROMPT = v2.SYSTEM_PROMPT
OUTPUT_INSTRUCTION = v2.OUTPUT_INSTRUCTION
STATIC_INSTRUCTION_HASH = v2.stable_hash([SYSTEM_PROMPT, OUTPUT_INSTRUCTION])
CUE_STRINGS = {
    "R0": "Policy relationship: whether the hidden decision policy governing the previous resolved cases is the same as the hidden decision policy governing the current case is not specified.",
    "RS": "Policy relationship: the previous resolved cases and the current case are governed by the same hidden decision policy for their corresponding attributes.",
    "RI": "Policy relationship: the hidden decision policy governing the previous resolved cases was generated independently of the hidden decision policy governing the current case.",
}
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
    return regime.relation_for(geometry, source, target) or "INDEPENDENT_POLICY"


def cross_domain_tasks() -> list[dict[str, Any]]:
    manifest = json.loads((V2_REPORT_ROOT / "manifest.json").read_text(encoding="utf-8"))
    return [task for task in manifest["tasks"] if task["condition"] == "transfer" and task["source"] != task["target"]]


def _source_policy_metadata(task: dict[str, Any]) -> dict[str, Any]:
    source = task["source"]; target_x = tuple(task["probe"]["x"])
    history = [V3Case(item["family"], tuple(item["x"]), tuple(item["y"])) for item in task["memory"]]
    env = generate_environment(task["geometry"], int(task["seed"]))
    posterior = posterior_predictive(env, source, source, history, target_x)
    action = solve(env.theta_by_family[source], target_x)
    labels = list(itertools.product((0, 1), repeat=3))
    return {"source_policy_action": list(action), "A_star_source": max(posterior),
            "p_true_source": posterior[labels.index(action)],
            "source_true_in_map": labels.index(action) in [i for i, p in enumerate(posterior) if abs(p - max(posterior)) <= 1e-12],
            "source_posterior": list(posterior)}


def render_user(task: dict[str, Any], arm: str) -> str:
    # The cue is the only intervention.  It precedes the unchanged V2 memory
    # renderer and therefore leaves history order, target wording, and schema
    # untouched.
    return CUE_STRINGS[arm] + "\n\n" + v2.render_user(task)


def build_tasks() -> list[dict[str, Any]]:
    base = cross_domain_tasks(); tasks: list[dict[str, Any]] = []
    for underlying in base:
        relation = relation_for(underlying["geometry"], underlying["source"], underlying["target"])
        metadata = _source_policy_metadata(underlying)
        underlying_id = stable_hash({"protocol": v2.PROTOCOL, "tasks_hash": json.loads((V2_REPORT_ROOT / "manifest.json").read_text())["tasks_hash"], "task": underlying})
        for arm in ARMS:
            task = json.loads(json.dumps(underlying))
            task.update({"protocol": PROTOCOL, "underlying_task_id": underlying_id, "arm": arm,
                         "actual_relation": relation, "cue_truthful": (arm == "R0") or (arm == "RS" and relation == "SAME_POLICY") or (arm == "RI" and relation == "INDEPENDENT_POLICY"),
                         "cue": CUE_STRINGS[arm], **metadata})
            task["prompt_hash"] = stable_hash({"system": SYSTEM_PROMPT, "user": render_user(task, arm)})
            task["static_instruction_hash"] = STATIC_INSTRUCTION_HASH
            tasks.append(task)
    # Interleave one randomly permuted arm per underlying stratum in each pass.
    rng = random.Random(EXECUTION_ORDER_SEED)
    groups: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for task in tasks: groups[task["underlying_task_id"]].append(task)
    group_items = list(groups.values()); rng.shuffle(group_items)
    ordered: list[dict[str, Any]] = []
    for group in group_items:
        group.sort(key=lambda task: ARMS.index(task["arm"]))
        if rng.random() < 0.5: group.reverse()
    for pass_index in range(len(ARMS)):
        for group in group_items:
            task = group[pass_index]; task["execution_order"] = len(ordered); ordered.append(task)
    return ordered


def expected_calls() -> dict[str, int]:
    return {"underlying": 1152, "arms": 3, "total": 3456}


def _recent_forecast(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    events = v2.v1._load_events(V2_DATA_ROOT / "events.jsonl")
    costs = [float(event["attempt_cost_usd"]) for event in events if event.get("task", {}).get("condition") == "transfer" and event.get("attempt_cost_usd") is not None]
    mean_cost = statistics.mean(costs) if costs else 0.0
    prompt_chars = [len(SYSTEM_PROMPT) + len(render_user(task, task["arm"])) for task in tasks]
    projected = mean_cost * len(tasks)
    return {"logical_calls": len(tasks), "projected_from_v2_transfer_cost_usd": projected,
            "safety_margin_50pct_usd": projected * 1.5, "hard_cap_usd": HARD_CAP_USD,
            "within_cap_with_margin": projected * 1.5 <= HARD_CAP_USD,
            "min_prompt_chars": min(prompt_chars), "max_prompt_chars": max(prompt_chars),
            "mean_prompt_chars": statistics.mean(prompt_chars), "v2_transfer_mean_cost_usd": mean_cost}


def freeze_manifest() -> dict[str, Any]:
    if any("[0,1,0]" in cue or "GLOBAL" in cue or "BLOCK" in cue or "DIAGONAL" in cue for cue in CUE_STRINGS.values()):
        raise RuntimeError("cue static leakage")
    tasks = build_tasks(); expected = expected_calls()
    if len(tasks) != expected["total"]: raise RuntimeError(f"count mismatch {len(tasks)}")
    # The execution list is deliberately interleaved, so ``tasks[::3]`` is not
    # a reliable representative of the underlying units.  Deduplicate by the
    # frozen underlying id before applying the identifiability gate.
    unique_underlying = {}
    for task in tasks:
        unique_underlying.setdefault(task["underlying_task_id"], task)
    ident = sum(float(task["A_star_source"]) >= 0.99 for task in unique_underlying.values())
    if ident / expected["underlying"] < 0.90: raise RuntimeError(f"source identifiability gate failed {ident}/{expected['underlying']}")
    forecast = _recent_forecast(tasks)
    if not forecast["within_cap_with_margin"]: raise RuntimeError(f"cost forecast exceeds cap: {forecast}")
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    write_csv(REPORT_ROOT / "source_policy_identifiability.csv", [{"underlying_task_id": task["underlying_task_id"], "geometry": task["geometry"], "seed": task["seed"], "source": task["source"], "target": task["target"], "probe_id": task["probe"]["case_id"], "actual_relation": task["actual_relation"], "A_star_source": task["A_star_source"], "p_true_source": task["p_true_source"]} for task in unique_underlying.values()])
    manifest = {"protocol": PROTOCOL, "created_at_utc": now(), "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "v2_protocol": v2.PROTOCOL, "v2_tasks_hash": json.loads((V2_REPORT_ROOT / "manifest.json").read_text())["tasks_hash"], "provider": "deepseek_direct", "model": MODEL, "thinking": "off", "seeds": list(SEEDS), "geometries": list(GEOMETRIES), "families": list(FAMILIES), "h": H, "arms": list(ARMS), "cue_strings": CUE_STRINGS, "execution_order_seed": EXECUTION_ORDER_SEED, "logical_calls": expected["total"], "call_breakdown": expected, "source_identifiability_count": ident, "source_identifiability_fraction": ident / expected["underlying"], "hard_cap_usd": HARD_CAP_USD, "forecast": forecast, "tasks": tasks}
    manifest["tasks_hash"] = stable_hash(tasks); path = REPORT_ROOT / "manifest.json"
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        if old.get("tasks_hash") != manifest["tasks_hash"]: raise RuntimeError("existing relation manifest differs")
        return old
    (REPORT_ROOT / "cue_strings.json").write_text(json.dumps(CUE_STRINGS, indent=2), encoding="utf-8")
    v2.atomic_json(path, manifest); return manifest


def _budget_change(*, reserve: float = 0.0, release: float = 0.0, actual: float = 0.0) -> dict[str, Any]:
    path = DATA_ROOT / "campaign_budget.json"; lock_path = path.with_suffix(".lock"); path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        budget = json.loads(path.read_text()) if path.exists() else {"protocol": PROTOCOL, "hard_cap_usd": HARD_CAP_USD, "spent_usd": 0.0, "reserved_usd": 0.0}
        spent, held = float(budget.get("spent_usd", 0.0)), float(budget.get("reserved_usd", 0.0))
        if held + 1e-12 < release or spent + held - release + reserve + actual > HARD_CAP_USD + 1e-12: raise RuntimeError("relation hard budget guard")
        budget.update(spent_usd=spent + actual, reserved_usd=held - release + reserve, updated_at_utc=now()); v2.atomic_json(path, budget); return budget


def _append(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n"); handle.flush()


def _cost(response: BackendResponse) -> float | None:
    from emergent_specialization.core.costs import estimate_usage_cost
    return estimate_usage_cost(response.token_usage, input_per_million_tokens=INPUT_PRICE, cached_input_per_million_tokens=CACHED_INPUT_PRICE, output_per_million_tokens=OUTPUT_PRICE)


async def run_real(*, confirm_real: bool = False) -> dict[str, Any]:
    if not confirm_real: raise SystemExit("relation campaign requires --confirm-real")
    manifest = json.loads((REPORT_ROOT / "manifest.json").read_text(encoding="utf-8")); events_path = DATA_ROOT / "events.jsonl"; status_path = DATA_ROOT / "run_status.json"
    if manifest.get("logical_calls") != 3456 or manifest.get("tasks_hash") != stable_hash(manifest["tasks"]): raise RuntimeError("relation manifest integrity failure")
    events = v2.v1._load_events(events_path); done = {e["logical_id"] for e in events if e.get("terminal")}; attempts = collections.defaultdict(int)
    for event in events: attempts[event["logical_id"]] = max(attempts[event["logical_id"]], int(event.get("attempt", 0)) + 1)
    status = json.loads(status_path.read_text()) if status_path.exists() else {"protocol": PROTOCOL, "status": "initialized", "tasks_hash": manifest["tasks_hash"], "logical_calls": 3456, "created_at_utc": now()}
    if status.get("tasks_hash") != manifest["tasks_hash"]: raise RuntimeError("status/manifest mismatch")
    status.update(status="running", started_or_resumed_at_utc=now()); v2.atomic_json(status_path, status)
    backend = None; spent = sum(float(e.get("attempt_cost_usd") or 0) for e in events); retries = sum(int(e.get("attempt", 0)) for e in events)
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
                    response = await backend.complete(system_prompt=SYSTEM_PROMPT, user_prompt=render_user(task, task["arm"]), model=MODEL, model_parameters={"thinking": "off", "max_tokens": 32})
                    cost = _cost(response)
                except Exception:
                    _budget_change(release=RESERVATION_USD); raise
                if cost is None:
                    _budget_change(release=RESERVATION_USD); raise RuntimeError("usage/cost unavailable")
                _budget_change(release=RESERVATION_USD, actual=cost); spent += cost
                decisions, parse_category = v2.v1.parse_decisions(response.raw_response); provider = response.provider_metadata or {}; category = response.error_category or parse_category; error = response.error or parse_category
                if provider.get("model") != MODEL: raise RuntimeError(f"model mismatch {provider.get('model')!r}")
                terminal = category == "out_of_domain" or (error is None and decisions is not None)
                event = {"protocol": PROTOCOL, "logical_id": logical_id, "attempt": attempt, "task": task, "decisions": decisions, "expected": task["probe"]["y"], "correct": decisions == task["probe"]["y"] if decisions is not None else False, "source_policy_correct": decisions == task["source_policy_action"] if decisions is not None else False, "error": error, "error_category": category, "terminal": terminal, "raw_model_response": response.raw_response, "latency_s": response.latency_s, "token_usage": response.token_usage, "provider_metadata": provider, "attempt_cost_usd": cost, "finished_at_utc": now()}
                _append(events_path, event); events.append(event)
                if terminal: done.add(logical_id); break
                if not response.retryable or category not in RETRYABLE: raise RuntimeError(f"non-retryable response {category}")
                retries += 1
            else: raise RuntimeError(f"retry exhaustion {logical_id}")
        if len(done) != 3456: raise RuntimeError(f"coverage {len(done)}/3456")
        status.update(status="completed", physical_attempts=len(events), retries=retries, observed_cost_usd=spent, finished_at_utc=now())
    except Exception as exc:
        status.update(status="incomplete", failure=f"{type(exc).__name__}: {exc}", physical_attempts=len(events), retries=retries, observed_cost_usd=spent, finished_at_utc=now())
    finally:
        if backend is not None: await backend.close()
        v2.atomic_json(status_path, status)
    return status


def main() -> None:
    parser = argparse.ArgumentParser(description=PROTOCOL); parser.add_argument("--freeze", action="store_true"); parser.add_argument("--run", action="store_true"); parser.add_argument("--confirm-real", action="store_true"); parser.add_argument("--analyze", action="store_true")
    args = parser.parse_args()
    if args.freeze: print(json.dumps((lambda m: {"manifest": str(REPORT_ROOT / "manifest.json"), "tasks_hash": m["tasks_hash"], "calls": m["call_breakdown"], "source_identifiability": [m["source_identifiability_count"], m["source_identifiability_fraction"]], "forecast": m["forecast"]})(freeze_manifest()), indent=2))
    elif args.run:
        import asyncio; print(json.dumps(asyncio.run(run_real(confirm_real=args.confirm_real)), indent=2))
    elif args.analyze: print(json.dumps(analyze(), indent=2, default=float))
    else: parser.error("choose --freeze, --run, or --analyze")


def analyze() -> dict[str, Any]:
    manifest = json.loads((REPORT_ROOT / "manifest.json").read_text(encoding="utf-8"))
    events = v2.v1._load_events(DATA_ROOT / "events.jsonl")
    grouped: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for event in events: grouped[event["logical_id"]].append(event)
    terminal: dict[str, dict[str, Any]] = {}
    for task in manifest["tasks"]:
        lid = stable_hash({"protocol": PROTOCOL, "tasks_hash": manifest["tasks_hash"], "task": task})
        values = [event for event in grouped.get(lid, []) if event.get("terminal")]
        if values: terminal[lid] = values[-1]
    if len(terminal) != manifest["logical_calls"]: raise RuntimeError(f"relation coverage {len(terminal)}/{manifest['logical_calls']}")

    response_rows: list[dict[str, Any]] = []
    for task in manifest["tasks"]:
        lid = stable_hash({"protocol": PROTOCOL, "tasks_hash": manifest["tasks_hash"], "task": task}); event = terminal[lid]
        decisions = tuple(event["decisions"]) if event.get("decisions") is not None else None; target = tuple(task["probe"]["y"]); source_action = tuple(task["source_policy_action"])
        response_rows.append({"arm": task["arm"], "geometry": task["geometry"], "seed": task["seed"], "source": task["source"], "target": task["target"], "probe_id": task["probe"]["case_id"], "underlying_task_id": task["underlying_task_id"], "actual_relation": task["actual_relation"], "cue_truthful": task["cue_truthful"], "A_star_source": task["A_star_source"], "source_policy_action": json.dumps(list(source_action)), "target_truth": json.dumps(list(target)), "decisions": json.dumps(list(decisions)) if decisions is not None else "", "correct": int(decisions == target) if decisions is not None else 0, "source_policy_correct": int(decisions == source_action) if decisions is not None else 0, "error_category": event.get("error_category") or "", "latency_s": event.get("latency_s"), "attempt_cost_usd": event.get("attempt_cost_usd"), "prompt_hash": task["prompt_hash"], "token_usage": json.dumps(event.get("token_usage") or {}), "model": (event.get("provider_metadata") or {}).get("model", "")})

    # Historical R_NONE rows: reuse V2 terminal observations and exact source
    # metadata from the frozen underlying tasks; no V2 inference is repeated.
    v2_manifest = json.loads((V2_REPORT_ROOT / "manifest.json").read_text(encoding="utf-8")); v2_tasks = [task for task in v2_manifest["tasks"] if task["condition"] == "transfer" and task["source"] != task["target"]]
    v2_events = v2.v1._load_events(V2_DATA_ROOT / "events.jsonl"); v2_grouped: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for event in v2_events: v2_grouped[event["logical_id"]].append(event)
    none_rows: list[dict[str, Any]] = []
    for task in v2_tasks:
        lid = v2.stable_hash({"protocol": v2.PROTOCOL, "tasks_hash": v2_manifest["tasks_hash"], "task": task}); values = [event for event in v2_grouped.get(lid, []) if event.get("terminal")]
        if not values: raise RuntimeError("missing V2 R_NONE terminal")
        event = values[-1]; metadata = _source_policy_metadata(task); decisions = tuple(event["decisions"]) if event.get("decisions") is not None else None; target = tuple(task["probe"]["y"]); source_action = tuple(metadata["source_policy_action"])
        none_rows.append({"arm": "R_NONE", "geometry": task["geometry"], "seed": task["seed"], "source": task["source"], "target": task["target"], "probe_id": task["probe"]["case_id"], "underlying_task_id": stable_hash({"protocol": v2.PROTOCOL, "tasks_hash": v2_manifest["tasks_hash"], "task": task}), "actual_relation": relation_for(task["geometry"], task["source"], task["target"]), "cue_truthful": None, "A_star_source": metadata["A_star_source"], "source_policy_action": json.dumps(list(source_action)), "target_truth": json.dumps(list(target)), "decisions": json.dumps(list(decisions)) if decisions is not None else "", "correct": int(decisions == target) if decisions is not None else 0, "source_policy_correct": int(decisions == source_action) if decisions is not None else 0, "error_category": event.get("error_category") or "", "latency_s": event.get("latency_s"), "attempt_cost_usd": event.get("attempt_cost_usd"), "prompt_hash": task["prompt_hash"], "token_usage": json.dumps(event.get("token_usage") or {}), "model": (event.get("provider_metadata") or {}).get("model", "")})
    all_rows = none_rows + response_rows; write_csv(REPORT_ROOT / "response_level.csv", all_rows)

    def mean(rows: list[dict[str, Any]], field: str) -> float:
        return statistics.mean(float(row[field]) for row in rows) if rows else float("nan")

    source_rows = []
    for arm in ("R_NONE",) + ARMS:
        for relation in ("SAME_POLICY", "INDEPENDENT_POLICY"):
            subset = [row for row in all_rows if row["arm"] == arm and row["actual_relation"] == relation]
            high = [row for row in subset if float(row["A_star_source"]) >= .99]
            source_rows.append({"arm": arm, "actual_relation": relation, "n": len(subset), "high_identifiability_n": len(high), "accuracy": mean(subset, "correct"), "source_policy_adherence": mean(subset, "source_policy_correct"), "high_accuracy": mean(high, "correct"), "high_source_policy_adherence": mean(high, "source_policy_correct")})
    write_csv(REPORT_ROOT / "signal_arm_summary.csv", source_rows)
    write_csv(REPORT_ROOT / "source_policy_adherence.csv", source_rows)

    arm_map = {(row["arm"], row["underlying_task_id"]): row for row in response_rows}
    seed_contrasts = []; truth_rows = []
    for seed in SEEDS:
        paired = [task for task in manifest["tasks"] if task["seed"] == seed and task["arm"] == "RS" and float(task["A_star_source"]) >= .99]
        gamma_values = [arm_map[("RS", task["underlying_task_id"])]["source_policy_correct"] - arm_map[("RI", task["underlying_task_id"])]["source_policy_correct"] for task in paired]
        seed_contrasts.append({"seed": seed, "n_high": len(paired), "Gamma_R_high": mean([{"v": value} for value in gamma_values], "v") if gamma_values else float("nan")})
        same = [task for task in manifest["tasks"] if task["seed"] == seed and task["arm"] == "RS" and task["actual_relation"] == "SAME_POLICY"]
        independent = [task for task in manifest["tasks"] if task["seed"] == seed and task["arm"] == "RS" and task["actual_relation"] == "INDEPENDENT_POLICY"]
        delta_same = mean([{"v": arm_map[("RS", t["underlying_task_id"])]["correct"] - arm_map[("RI", t["underlying_task_id"])]["correct"]} for t in same], "v")
        delta_ind = mean([{"v": arm_map[("RI", t["underlying_task_id"])]["correct"] - arm_map[("RS", t["underlying_task_id"])]["correct"]} for t in independent], "v")
        truth_rows.append({"seed": seed, "n_same": len(same), "n_independent": len(independent), "Delta_same": delta_same, "Delta_independent": delta_ind, "Upsilon_R": .5 * (delta_same + delta_ind)})
    write_csv(REPORT_ROOT / "seed_level_contrasts.csv", seed_contrasts); write_csv(REPORT_ROOT / "truth_interaction.csv", truth_rows)

    gamma_high = mean([{"v": row["Gamma_R_high"]} for row in seed_contrasts], "v")
    delta_same = mean([{"v": row["Delta_same"]} for row in truth_rows], "v"); delta_ind = mean([{"v": row["Delta_independent"]} for row in truth_rows], "v"); upsilon = .5 * (delta_same + delta_ind)

    # Truthful-R matrix: retain V2 empty-memory baseline and select RS for true
    # shared pairs, RI for true independent pairs. Same-family diagonal cells are
    # intentionally reused from V2 and are not newly inferred here.
    v2_baseline: dict[tuple[Any, ...], dict[str, Any]] = {}
    v2_terminal_all = v2.v1._load_events(V2_DATA_ROOT / "events.jsonl"); v2_group_all: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for event in v2_terminal_all: v2_group_all[event["logical_id"]].append(event)
    for task in v2_manifest["tasks"]:
        if task["condition"] != "baseline": continue
        lid = v2.stable_hash({"protocol": v2.PROTOCOL, "tasks_hash": v2_manifest["tasks_hash"], "task": task}); value = [e for e in v2_group_all.get(lid, []) if e.get("terminal")][-1]
        v2_baseline[(task["geometry"], task["seed"], task["target"], task["probe"]["case_id"])] = {"correct": int(value.get("correct", False))}
    # The truthful matrix contains all V2 transfer cells.  Same-family
    # diagonals are reused from V2; cross-family cells select the cue arm whose
    # statement matches the frozen relation oracle.
    truthful_rows = []
    v2_transfer_all = [task for task in v2_manifest["tasks"] if task["condition"] == "transfer"]
    for task in v2_transfer_all:
        relation = relation_for(task["geometry"], task["source"], task["target"])
        task_id = stable_hash({"protocol": v2.PROTOCOL, "tasks_hash": v2_manifest["tasks_hash"], "task": task})
        if task["source"] == task["target"]:
            values = [e for e in v2_grouped.get(task_id, []) if e.get("terminal")]
            if not values:
                raise RuntimeError(f"missing V2 same-family terminal {task_id}")
            event = values[-1]
            decisions = tuple(event["decisions"]) if event.get("decisions") is not None else None
            metadata = _source_policy_metadata(task)
            selected = {"correct": int(decisions == tuple(task["probe"]["y"])) if decisions is not None else 0,
                        "source_policy_correct": int(decisions == tuple(metadata["source_policy_action"])) if decisions is not None else 0}
        else:
            selected = arm_map[("RS" if relation == "SAME_POLICY" else "RI", task_id)]
        base = v2_baseline[(task["geometry"], task["seed"], task["target"], task["probe"]["case_id"])]
        truthful_rows.append({"geometry": task["geometry"], "seed": task["seed"], "source": task["source"], "target": task["target"], "probe_id": task["probe"]["case_id"], "actual_relation": relation, "transfer_accuracy": selected["correct"], "baseline_accuracy": base["correct"], "L_DS_R_true": selected["correct"] - base["correct"], "source_policy_adherence": selected["source_policy_correct"], "reused_v2": int(task["source"] == task["target"])})
    write_csv(REPORT_ROOT / "truthful_relation_transfer_matrices.csv", truthful_rows)

    def matrix_metrics(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        result = []
        for geometry in GEOMETRIES:
            cells: dict[tuple[str, str], list[float]] = collections.defaultdict(list)
            for row in rows:
                if row["geometry"] == geometry: cells[(row["source"], row["target"])].append(float(row[key]))
            values = {cell: statistics.mean(value) for cell, value in cells.items()}; diag = statistics.mean(values[(f, f)] for f in FAMILIES) if all((f, f) in values for f in FAMILIES) else float("nan"); off = statistics.mean(values[(s, t)] for s in FAMILIES for t in FAMILIES if s != t) if all((s, t) in values for s in FAMILIES for t in FAMILIES if s != t) else float("nan")
            within_keys = (("ACCESS", "RELEASE"), ("RELEASE", "ACCESS"), ("INCIDENT", "PROVENANCE"), ("PROVENANCE", "INCIDENT")); independent = [(s, t) for s in FAMILIES for t in FAMILIES if s != t and relation_for(geometry, s, t) == "INDEPENDENT_POLICY"]
            w = statistics.mean(values[k] for k in within_keys if k in values) if any(k in values for k in within_keys) else float("nan"); c = statistics.mean(values[k] for k in independent if k in values) if any(k in values for k in independent) else 0.0
            result.append({"geometry": geometry, "D": diag, "O": off, "Q": diag - off, "W": w, "C": c, "B": w - c})
        return result
    geometry_metrics = matrix_metrics(truthful_rows, "L_DS_R_true"); write_csv(REPORT_ROOT / "truthful_relation_geometry_metrics.csv", geometry_metrics)

    # Relation-aware exact oracle and matrix alignment.
    oracle_rows = regime.build_oracle_rows(v2_manifest)["relation"]; oracle_cells: dict[tuple[Any, ...], list[float]] = collections.defaultdict(list)
    for row in oracle_rows:
        if row["condition"] == "transfer": oracle_cells[(row["geometry"], row["source"], row["target"])].append(float(row["A_star"]) - .125)
    cell_rows = []
    for geometry in GEOMETRIES:
        for source in FAMILIES:
            for target in FAMILIES:
                observed = [row for row in truthful_rows if row["geometry"] == geometry and row["source"] == source and row["target"] == target]
                l_ds = statistics.mean(float(row["L_DS_R_true"]) for row in observed)
                l_star = statistics.mean(oracle_cells[(geometry, source, target)])
                cell_rows.append({"geometry": geometry, "source": source, "target": target, "actual_relation": relation_for(geometry, source, target), "L_DS": l_ds, "L_star_relation": l_star, "zero_information": int(abs(l_star) <= 1e-12), "missed_transfer": l_star - l_ds})
    write_csv(REPORT_ROOT / "missed_transfer.csv", cell_rows)
    write_csv(REPORT_ROOT / "zero_information_transfer.csv", [row for row in cell_rows if row["zero_information"]])
    oracle_lookup = {(row["geometry"], row["source"], row["target"]): float(row["L_star_relation"]) for row in cell_rows}
    for row in truthful_rows:
        row["L_star_relation"] = oracle_lookup[(row["geometry"], row["source"], row["target"])]
    write_csv(REPORT_ROOT / "truthful_relation_transfer_matrices.csv", truthful_rows)
    lds_vector = np.array([float(row["L_DS"]) for row in cell_rows]); lstar_vector = np.array([float(row["L_star_relation"]) for row in cell_rows])
    alpha = float(np.dot(lds_vector, lstar_vector) / np.dot(lstar_vector, lstar_vector)) if np.dot(lstar_vector, lstar_vector) else float("nan")
    projection_rows = [{"geometry": "ALL", "alpha": alpha, "lds_frobenius": float(np.linalg.norm(lds_vector)), "lstar_frobenius": float(np.linalg.norm(lstar_vector)), "residual_frobenius": float(np.linalg.norm(lds_vector - alpha * lstar_vector))}]
    residual_rows = []
    for row in cell_rows:
        residual_rows.append({**row, "alpha": alpha, "residual": float(row["L_DS"]) - alpha * float(row["L_star_relation"])})
    write_csv(REPORT_ROOT / "learner_projection.csv", projection_rows)
    write_csv(REPORT_ROOT / "residual_transfer.csv", residual_rows)
    relation_alignment = []
    relation_seed_alignment = []
    def _cosine(left: np.ndarray, right: np.ndarray, centered: bool = False) -> float | None:
        if centered:
            p = np.eye(4) - np.ones((4, 4)) / 4
            left, right = p @ left @ p, p @ right @ p
        denominator = np.linalg.norm(left) * np.linalg.norm(right)
        return float(np.sum(left * right) / denominator) if denominator else None
    for geometry in GEOMETRIES:
        ds = np.zeros((4, 4)); oracle = np.zeros((4, 4)); indexes = {family: i for i, family in enumerate(FAMILIES)}
        for row in cell_rows:
            if row["geometry"] == geometry: ds[indexes[row["source"]], indexes[row["target"]]] = float(row["L_DS"])
        for source in FAMILIES:
            for target in FAMILIES: oracle[indexes[source], indexes[target]] = statistics.mean(oracle_cells[(geometry, source, target)])
        relation_alignment.append({"geometry": geometry, "raw_cosine": _cosine(ds, oracle), "centered_cosine": _cosine(ds, oracle, centered=True)})
        for seed in SEEDS:
            ds_seed = np.zeros((4, 4)); oracle_seed = np.zeros((4, 4))
            for source in FAMILIES:
                for target in FAMILIES:
                    cell = [row for row in truthful_rows if row["geometry"] == geometry and row["seed"] == seed and row["source"] == source and row["target"] == target]
                    ds_seed[indexes[source], indexes[target]] = statistics.mean(float(row["L_DS_R_true"]) for row in cell)
                    oracle_seed[indexes[source], indexes[target]] = statistics.mean(oracle_cells[(geometry, source, target)])
            relation_seed_alignment.append({"geometry": geometry, "seed": seed, "raw_cosine": _cosine(ds_seed, oracle_seed), "centered_cosine": _cosine(ds_seed, oracle_seed, centered=True)})
    write_csv(REPORT_ROOT / "relation_oracle_seed_alignment.csv", relation_seed_alignment)
    write_csv(REPORT_ROOT / "relation_oracle_alignment.csv", relation_alignment)

    component_rows = []
    for bit in range(3):
        for arm in ("RS", "RI"):
            for relation in regime.RELATION_LABELS:
                subset = [row for row in response_rows if row["arm"] == arm and row["actual_relation"] == relation]
                valid = [row for row in subset if row["decisions"]]
                component_rows.append({"component": bit + 1, "arm": arm, "actual_relation": relation, "n": len(subset), "valid_n": len(valid), "target_accuracy": statistics.mean(int(json.loads(row["decisions"])[bit] == json.loads(row["target_truth"])[bit]) for row in valid) if valid else float("nan"), "source_policy_adherence": statistics.mean(int(json.loads(row["decisions"])[bit] == json.loads(row["source_policy_action"])[bit]) for row in valid) if valid else float("nan")})
    write_csv(REPORT_ROOT / "component_signal_effects.csv", component_rows)
    pair_rows = []
    for arm in ("R_NONE",) + ARMS:
        for source in FAMILIES:
            for target in FAMILIES:
                subset = [row for row in all_rows if row["arm"] == arm and row["source"] == source and row["target"] == target]
                pair_rows.append({"arm": arm, "source": source, "target": target, "actual_relation": relation_for(subset[0]["geometry"], source, target) if subset else "", "n": len(subset), "accuracy": mean(subset, "correct"), "source_policy_adherence": mean(subset, "source_policy_correct")})
    write_csv(REPORT_ROOT / "semantic_pair_effects.csv", pair_rows)

    anchoring_rows = []
    for row in response_rows:
        task = next(task for task in manifest["tasks"] if task["underlying_task_id"] == row["underlying_task_id"] and task["arm"] == row["arm"])
        decisions = json.loads(row["decisions"]) if row["decisions"] else None; labels = [item["y"] for item in task["memory"]]; counts = collections.Counter(tuple(label) for label in labels)
        anchoring_rows.append({"arm": row["arm"], "actual_relation": row["actual_relation"], "seed": row["seed"], "any_action_copy": int(decisions is not None and any(decisions == label for label in labels)), "last_action_copy": int(decisions is not None and labels and decisions == labels[-1]), "modal_memory_copy": int(decisions is not None and labels and decisions == list(counts.most_common(1)[0][0]))})
    write_csv(REPORT_ROOT / "anchoring.csv", anchoring_rows)

    distribution_rows = []
    for arm in ("R_NONE",) + ARMS:
        subset = [row for row in all_rows if row["arm"] == arm]; values = [tuple(json.loads(row["decisions"])) for row in subset if row["decisions"]]; counts = collections.Counter(values); entropy = -sum((n / len(values)) * math.log2(n / len(values)) for n in counts.values()) if values else float("nan")
        distribution_rows.append({"arm": arm, "n": len(values), "invalid_n": len(subset) - len(values), "modal_output": json.dumps(list(counts.most_common(1)[0][0])) if values else "", "modal_fraction": counts.most_common(1)[0][1] / len(values) if values else float("nan"), "output_entropy_bits": entropy, "bit1_one_rate": statistics.mean(v[0] for v in values) if values else float("nan"), "bit2_one_rate": statistics.mean(v[1] for v in values) if values else float("nan"), "bit3_one_rate": statistics.mean(v[2] for v in values) if values else float("nan")})
    write_csv(REPORT_ROOT / "response_distribution.csv", distribution_rows)

    health = {"protocol": PROTOCOL, "logical_expected": 3456, "logical_terminal": len(terminal), "physical_attempts": len(events), "technical_retries": sum(int(e.get("attempt", 0)) for e in events), "semantic_ood": sum(e.get("error_category") == "out_of_domain" for e in events), "coverage": len(terminal) / 3456, "models": sorted({(e.get("provider_metadata") or {}).get("model") for e in events}), "fingerprints": sorted({(e.get("provider_metadata") or {}).get("system_fingerprint") for e in events}), "observed_cost_usd": sum(float(e.get("attempt_cost_usd") or 0) for e in events), "usage_coverage": sum(bool(e.get("token_usage")) for e in events) / len(events), "classification": "CLEAN" if len(terminal) == 3456 and not any(e.get("error_category") in RETRYABLE for e in events) else "COMPLETE_WITH_RETRIES"}
    v2.atomic_json(REPORT_ROOT / "technical_health.json", health); v2.atomic_json(REPORT_ROOT / "cost.json", {"observed_cost_usd": health["observed_cost_usd"], "hard_cap_usd": HARD_CAP_USD, "remaining_usd": HARD_CAP_USD - health["observed_cost_usd"]})
    figures = REPORT_ROOT / "figures"; figures.mkdir(parents=True, exist_ok=True)
    for geometry in GEOMETRIES:
        values = np.zeros((4, 4)); index = {family: i for i, family in enumerate(FAMILIES)}
        for row in truthful_rows:
            if row["geometry"] == geometry: values[index[row["source"]], index[row["target"]]] = statistics.mean(float(x["L_DS_R_true"]) for x in truthful_rows if x["geometry"] == geometry and x["source"] == row["source"] and x["target"] == row["target"])
        v2.v1._svg_heatmap(figures / f"truthful_R_{geometry.lower()}.svg", values, f"Truthful R {geometry}")
    r_none_cross_accuracy = mean([row for row in none_rows], "correct")
    rs_same_accuracy = mean([row for row in response_rows if row["arm"] == "RS" and row["actual_relation"] == "SAME_POLICY"], "correct")
    seed_alignment_values = [float(row["raw_cosine"]) for row in relation_seed_alignment if row["raw_cosine"] is not None]
    zero_values = [float(row["L_DS"]) for row in cell_rows if row["zero_information"]]
    summary = {"protocol": PROTOCOL, "logical_calls": 3456, "physical_attempts": len(events), "health": health, "Gamma_R_high": gamma_high, "seed_Gamma_R": seed_contrasts, "Delta_same": delta_same, "Delta_independent": delta_ind, "Upsilon_R": upsilon, "r_none_cross_accuracy": r_none_cross_accuracy, "rs_same_accuracy": rs_same_accuracy, "rs_same_minus_r_none_cross": rs_same_accuracy - r_none_cross_accuracy, "seed_truth_interaction": truth_rows, "truthful_geometry": geometry_metrics, "relation_alignment": relation_alignment, "relation_seed_alignment": relation_seed_alignment, "learner_projection_alpha": alpha, "mean_missed_transfer": statistics.mean(float(row["missed_transfer"]) for row in cell_rows), "mean_zero_information_transfer": statistics.mean(zero_values) if zero_values else None, "zero_information_cell_count": len(zero_values), "source_identifiability": {"count": manifest["source_identifiability_count"], "fraction": manifest["source_identifiability_fraction"]}, "gates": {"R1_Gamma": gamma_high >= .10 and sum(float(row["Gamma_R_high"]) > 0 for row in seed_contrasts) >= 3, "R2_true_same_accuracy": delta_same >= .10 and rs_same_accuracy > r_none_cross_accuracy, "R3_source_adherence": mean([row for row in source_rows if row["arm"] == "RS" and row["actual_relation"] == "SAME_POLICY"], "high_source_policy_adherence") >= .30, "R4_Upsilon": upsilon >= .10 and sum(float(row["Upsilon_R"]) > 0 for row in truth_rows) >= 3, "R5_block": geometry_metrics[1]["W"] > 0 and geometry_metrics[1]["B"] >= .05, "R6_ordering": geometry_metrics[0]["Q"] < geometry_metrics[1]["Q"] < geometry_metrics[2]["Q"], "R7_alignment": sum(value > 0 for value in seed_alignment_values) >= 3 and any(row["raw_cosine"] is not None and row["raw_cosine"] > 0 for row in relation_alignment)}}
    summary["classification"] = "RELATION-CONTROLLED TRANSFER ESTABLISHED" if all(summary["gates"].values()) else ("PARTIAL RELATION CONTROL" if any(summary["gates"].values()) else "NO RELATION CONTROL")
    v2.atomic_json(REPORT_ROOT / "analysis_summary.json", summary); return summary


if __name__ == "__main__":
    main()
