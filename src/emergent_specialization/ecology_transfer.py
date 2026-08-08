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
import statistics
import tempfile
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .credentials import CredentialStore
from .explicit_rule_execution import _append_event, _atomic_json
from .models import BackendResponse
from .providers import DeepSeekDirectBackend
from .semantic_ecology import ECOLOGIES, Ecology, Environment, parse_action, stable_hash

ROOT = Path(__file__).resolve().parents[2]
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
    h4 = __import__("emergent_specialization.semantic_ecology", fromlist=["predictive_identifiability"]).predictive_identifiability(ecology, env, family, 4)
    h8 = __import__("emergent_specialization.semantic_ecology", fromlist=["predictive_identifiability"]).predictive_identifiability(ecology, env, family, 8)
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
    from .semantic_ecology import Case
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
    if held + 1e-12 < release or spent + held - release + reserve > GLOBAL_CAP + 1e-12:
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
    from .costs import estimate_usage_cost
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
    if events_path.exists() or status_path.exists():
        raise RuntimeError("transfer output already exists; no duplicate run")
    status = {"protocol": manifest["protocol"], "ecology": ecology_name, "status": "initialized",
              "tasks_hash": manifest["tasks_hash"], "logical_calls": 1920, "created_at_utc": now()}
    _atomic_json(status_path, status)
    backend = None; events: list[dict[str, Any]] = []; cost_total = 0.0; physical = 0; retries = 0
    try:
        key = CredentialStore().get(source="keychain")
        backend = DeepSeekDirectBackend(api_key=key, thinking="off", max_tokens=256)
        ecology = ECOLOGIES[ecology_name]
        for task in manifest["tasks"]:
            logical_id = stable_hash({"ecology": ecology_name, "task": task, "tasks_hash": manifest["tasks_hash"]})
            for attempt in range(2):
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
                if error is None:
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


def aggregate(ecology_name: str) -> dict[str, Any]:
    path = OUTPUT_ROOT / ecology_name.lower() / "events.jsonl"
    events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    grouped: dict[tuple[int, str, str | None, int], list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        task = event["task"]; grouped[(task["seed"], task["target"], task["source"], task["h"])].append(event)
    rows: list[dict[str, Any]] = []
    for (seed, target, source, h), values in sorted(grouped.items()):
        valid = [v for v in values if v.get("error") is None and v.get("answer") is not None]
        rows.append({"ecology": ecology_name, "seed": seed, "source": source or "none", "target": target, "h": h,
                     "n": len(valid), "accuracy": sum(v["correct"] for v in valid) / len(valid) if valid else None,
                     "mean_confidence": sum(float(v["confidence"]) for v in valid) / len(valid) if valid else None,
                     "errors": len(values) - len(valid)})
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    out = REPORT_ROOT / f"{ecology_name.lower()}_aggregate.json"; _atomic_json(out, {"rows": rows, "ecology": ecology_name}); return {"rows": rows}


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
