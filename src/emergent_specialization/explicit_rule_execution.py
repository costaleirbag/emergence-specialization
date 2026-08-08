"""AR-001 isolated explicit-rule diagnostic with fail-closed execution controls."""

from __future__ import annotations

import argparse
import asyncio
import csv
import fcntl
import hashlib
import json
import math
import os
import subprocess
import tempfile
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Awaitable, Callable

import yaml

from .costs import estimate_usage_cost, summarize_usage
from .credentials import CredentialStore
from .environment import HIDDEN_RULES, HiddenWorldEnvironment
from .models import BackendResponse
from .parsing import ResponseParseError, parse_agent_output
from .providers import DeepSeekDirectBackend

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "configs/research/auto/explicit_rule_execution_v1.yaml"
SYSTEM_PROMPT = "You execute the explicitly supplied arithmetic rule exactly and return only the requested JSON."
ALLOWED_RETRY_CATEGORIES = frozenset({"parse_error", "empty_content", "transient_transport", "transport"})
EXPECTED_CONFIG: dict[str, Any] = {
    "protocol": "AR-001-explicit-rule-execution-v1", "backend": "deepseek_direct", "model": "deepseek-v4-flash",
    "probe_set_path": "data/calibrations/memory-representation-thinking-v1/balanced_probe_set.json",
    "probe_hash": "7c5370122b553dafbd1ef950f3b4de9ca9636f7c3922cb31800169638b59c2df",
    "replicates": 3, "thinking": "off", "max_tokens": 128, "technical_retries": 1,
    "max_physical_attempts": 336, "hard_cost_cap_usd": 0.05, "max_attempt_cost_reserve_usd": 0.005,
    "max_billed_input_tokens_per_call": 32768,
    "global_cost_ledger_path": "reports/auto-research/cost_ledger.csv", "global_cost_cap_usd": 2.0,
    "session_id": "autonomous-session-2026-08-08", "credential_source": "keychain",
    "credential_service": "emergence-specialization.deepseek", "credential_account": "api",
    "input_per_million_tokens": 0.14, "cached_input_per_million_tokens": 0.0028,
    "output_per_million_tokens": 0.28, "output_dir": "data/auto-research/explicit-rule-execution-v1",
    "report_dir": "reports/auto-research/explicit-rule-execution-v1",
}


def _utc() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


def _append_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n"); handle.flush(); os.fsync(handle.fileno())


def _load_config(path: str | Path = DEFAULT_CONFIG) -> tuple[dict[str, Any], str]:
    config_path = Path(path).resolve(); raw = config_path.read_bytes(); value = yaml.safe_load(raw)
    if value != EXPECTED_CONFIG:
        missing = sorted(set(EXPECTED_CONFIG) - set(value or {})); extra = sorted(set(value or {}) - set(EXPECTED_CONFIG))
        changed = sorted(k for k in set(EXPECTED_CONFIG) & set(value or {}) if value[k] != EXPECTED_CONFIG[k])
        raise ValueError(f"frozen AR-001 config mismatch: missing={missing}, extra={extra}, changed={changed}")
    return value, _sha256(raw)


def probes(config: dict[str, Any]) -> list[dict[str, Any]]:
    payload = json.loads((ROOT / config["probe_set_path"]).read_text(encoding="utf-8")); tasks = payload["tasks"]
    calculated = _sha256(json.dumps(tasks, sort_keys=True, separators=(",", ":")).encode())
    if payload.get("probe_hash") != config["probe_hash"] or calculated != config["probe_hash"]: raise ValueError("frozen probe hash mismatch")
    env = HiddenWorldEnvironment()
    if len(tasks) != 56 or any(sum(t["world"] == w and t["correct_answer"] == z for t in tasks) != 2 for w in env.worlds for z in range(7)): raise ValueError("balanced-probe invariant failed")
    if any(env.answer_for(t["world"], int(t["x"]), int(t["y"])) != int(t["correct_answer"]) for t in tasks): raise ValueError("probe labels invalid")
    return tasks


def prompt(task: dict[str, Any]) -> str:
    a, b, c = HIDDEN_RULES[str(task["world"])]
    return (f"This is an isolated diagnostic. World {task['world']} has the explicit correct formula "
            f"z=({a}*x+{b}*y+{c}) mod 7. For x={task['x']} and y={task['y']}, compute z.\n"
            'Return only a JSON object matching exactly {"answer": <integer 0..6>, "confidence": <number 0..1>}.')


def _path(config_value: str, override: str | Path | None) -> Path:
    return Path(override).resolve() if override is not None else (ROOT / config_value).resolve()


def _read_ledger(path: Path, session_id: str, global_cap: float) -> tuple[list[dict[str, str]], dict[str, str]]:
    if not path.exists(): raise RuntimeError("authoritative global cost ledger is missing")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle); fields = set(reader.fieldnames or []); rows = list(reader)
    required = {"session_id", "global_budget_usd", "spent_usd", "reserved_usd", "status", "updated_at_utc", "ar001_spent_usd", "ar001_reserved_usd"}
    if not required <= fields: raise RuntimeError(f"cost-ledger schema missing columns: {sorted(required - fields)}")
    matches = [r for r in rows if r.get("session_id") == session_id]
    if len(matches) != 1: raise RuntimeError("authoritative session cost-ledger row missing or duplicated")
    row = matches[0]
    if float(row["global_budget_usd"]) != global_cap or row.get("status") != "open": raise RuntimeError("cost-ledger budget/state mismatch")
    for key in ("spent_usd", "reserved_usd", "ar001_spent_usd", "ar001_reserved_usd"):
        value = float(row[key])
        if not math.isfinite(value) or value < 0: raise RuntimeError("invalid cost-ledger amount")
    return rows, row


def _write_ledger(path: Path, rows: list[dict[str, str]]) -> None:
    required = ["session_id", "global_budget_usd", "spent_usd", "reserved_usd", "status", "updated_at_utc", "ar001_spent_usd", "ar001_reserved_usd"]
    # Preserve all pre-existing columns and rows; the session-row schema only
    # requires these six fields and never rewrites the ledger to a narrower form.
    fields = required + sorted({key for row in rows for key in row} - set(required))
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows); handle.flush(); os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


def _ledger_change(path: Path, config: dict[str, Any], *, reserve: float = 0.0, reconcile_reserved: float = 0.0, actual: float = 0.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); lock_path = path.with_suffix(path.suffix + ".lock")
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        rows, row = _read_ledger(path, config["session_id"], float(config["global_cost_cap_usd"]))
        spent, reserved = float(row["spent_usd"]), float(row["reserved_usd"])
        experiment_spent, experiment_reserved = float(row["ar001_spent_usd"]), float(row["ar001_reserved_usd"])
        if reconcile_reserved:
            if reserved + 1e-12 < reconcile_reserved or experiment_reserved + 1e-12 < reconcile_reserved: raise RuntimeError("cost-ledger reservation reconciliation mismatch")
            reserved -= reconcile_reserved; spent += actual; experiment_reserved -= reconcile_reserved; experiment_spent += actual
        if reserve:
            if spent + reserved + reserve > float(config["global_cost_cap_usd"]) + 1e-12: raise RuntimeError("global cumulative cost guard")
            reserved += reserve; experiment_reserved += reserve
        row.update(spent_usd=f"{spent:.9f}", reserved_usd=f"{reserved:.9f}", ar001_spent_usd=f"{experiment_spent:.9f}", ar001_reserved_usd=f"{experiment_reserved:.9f}", updated_at_utc=_utc())
        _write_ledger(path, rows)


def _git_head() -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def _implementation_provenance() -> dict[str, Any]:
    module_path = Path(__file__).resolve()
    status = subprocess.run(["git", "status", "--porcelain", "--", str(module_path), str(DEFAULT_CONFIG), EXPECTED_CONFIG["probe_set_path"]], cwd=ROOT, check=True, capture_output=True, text=True).stdout
    return {"implementation_sha256": _sha256(module_path.read_bytes()), "git_head": _git_head(),
            "scientific_worktree_state": "clean" if not status.strip() else "uncommitted_sha256_frozen",
            "scientific_worktree_status_sha256": _sha256(status.encode())}


def _validate_reservation(config: dict[str, Any], tasks: list[dict[str, Any]]) -> float:
    input_bound = int(config["max_billed_input_tokens_per_call"])
    if input_bound <= 0: raise ValueError("max billed input token bound must be positive")
    # UTF-8 bytes upper-bound tokenizer input units; 4096 additional units
    # conservatively cover chat framing/provider envelope fields.
    if any(len(SYSTEM_PROMPT.encode()) + len(prompt(task).encode()) + 4096 > input_bound for task in tasks):
        raise ValueError("rendered prompt exceeds frozen billed-input reservation bound")
    upper = input_bound * float(config["input_per_million_tokens"]) / 1_000_000 + int(config["max_tokens"]) * float(config["output_per_million_tokens"]) / 1_000_000
    if upper > float(config["max_attempt_cost_reserve_usd"]) + 1e-12: raise ValueError("frozen per-call reservation is below the configured price/token upper bound")
    return upper


def _identity(config: dict[str, Any], config_hash: str, task: dict[str, Any], replicate: int) -> tuple[str, str, str]:
    user = prompt(task); prompt_hash = _sha256(user.encode()); system_hash = _sha256(SYSTEM_PROMPT.encode())
    payload = {"protocol": config["protocol"], "task": task, "replicate": replicate, "system_prompt_hash": system_hash,
               "prompt_hash": prompt_hash, "model": config["model"], "model_parameters": {"thinking": "off", "max_tokens": 128},
               "config_hash": config_hash, "probe_hash": config["probe_hash"]}
    return _sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()), prompt_hash, system_hash


def preflight(path: str | Path = DEFAULT_CONFIG, *, ledger_path: str | Path | None = None) -> dict[str, Any]:
    config, config_hash = _load_config(path); tasks = probes(config); upper = _validate_reservation(config, tasks); ledger = _path(config["global_cost_ledger_path"], ledger_path)
    _, row = _read_ledger(ledger, config["session_id"], float(config["global_cost_cap_usd"]))
    available = float(config["global_cost_cap_usd"]) - float(row["spent_usd"]) - float(row["reserved_usd"])
    if available + 1e-12 < float(config["hard_cost_cap_usd"]): raise RuntimeError("prior cost plus experiment cap exceeds global cap")
    return {"protocol": config["protocol"], "config_hash": config_hash, "probe_hash": config["probe_hash"], "logical_calls": len(tasks) * config["replicates"],
            "physical_attempt_cap": config["max_physical_attempts"], "hard_cost_cap_usd": config["hard_cost_cap_usd"], "global_available_usd": available,
            "max_attempt_cost_reserve_usd": config["max_attempt_cost_reserve_usd"], "ledger_schema": ["session_id", "global_budget_usd", "spent_usd", "reserved_usd", "status", "updated_at_utc", "ar001_spent_usd", "ar001_reserved_usd"],
            "demonstrated_attempt_cost_upper_bound_usd": upper, "implementation_provenance": _implementation_provenance(),
            "balance": {w: {z: sum(t["world"] == w and t["correct_answer"] == z for t in tasks) for z in range(7)} for w in HIDDEN_RULES},
            "credential_accessed": False, "network_accessed": False}


def _attempt_cost(response: BackendResponse, config: dict[str, Any]) -> tuple[float | None, str | None]:
    if response.observed_cost_usd is not None:
        value = float(response.observed_cost_usd)
        return (value, "provider_reported") if math.isfinite(value) and value >= 0 else (None, None)
    estimate = estimate_usage_cost(response.token_usage, input_per_million_tokens=config["input_per_million_tokens"], cached_input_per_million_tokens=config["cached_input_per_million_tokens"], output_per_million_tokens=config["output_per_million_tokens"])
    return (float(estimate), "configured_estimate") if estimate is not None else (None, None)


async def _default_sleep(seconds: float) -> None:
    await asyncio.sleep(seconds)


async def _close_backend(backend: Any) -> None:
    close = getattr(backend, "close", None)
    if callable(close):
        result = close()
        if hasattr(result, "__await__"): await result


async def _run_real_locked(path: str | Path = DEFAULT_CONFIG, *, confirm_real: bool = False, backend: Any = None,
                   output_dir: str | Path | None = None, ledger_path: str | Path | None = None,
                   sleep: Callable[[float], Awaitable[None]] = _default_sleep) -> dict[str, Any]:
    if not confirm_real: raise SystemExit("real inference requires --confirm-real")
    config, config_hash = _load_config(path); tasks = probes(config); reservation_upper = _validate_reservation(config, tasks); provenance = _implementation_provenance(); output = _path(config["output_dir"], output_dir); ledger = _path(config["global_cost_ledger_path"], ledger_path)
    output.mkdir(parents=True, exist_ok=True); events_path, manifest_path = output / "events.jsonl", output / "manifest.json"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()] if events_path.exists() else []
    base_manifest = {"protocol": config["protocol"], "status": "initialized", "config_hash": config_hash, "git_head": provenance["git_head"], "probe_hash": config["probe_hash"],
                "model": config["model"], "backend": config["backend"], "thinking": config["thinking"], "max_tokens": config["max_tokens"],
                "planned_logical_queries": 168, "max_physical_attempts": 336, "hard_cost_cap_usd": 0.05,
                "max_attempt_cost_reserve_usd": config["max_attempt_cost_reserve_usd"],
                "demonstrated_attempt_cost_upper_bound_usd": reservation_upper, **provenance,
                "pricing_per_million_tokens": {"input": 0.14, "cached_input": 0.0028, "output": 0.28},
                "technical_retry_policy": sorted(ALLOWED_RETRY_CATEGORIES), "created_at_utc": _utc()}
    if events:
        if not manifest_path.exists():
            manifest = {**base_manifest, "status": "failed", "failure": "events exist without a manifest", "finished_at_utc": _utc()}; _atomic_json(manifest_path, manifest); await _close_backend(backend); return manifest
        try: manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            manifest = {**base_manifest, "status": "failed", "failure": f"unreadable prior manifest: {exc}", "finished_at_utc": _utc()}; _atomic_json(manifest_path, manifest); await _close_backend(backend); return manifest
        if manifest.get("status") in {"invalid_model", "failed", "budget_violation", "guard_stopped"}:
            await _close_backend(backend); return manifest
        compatibility = {key: base_manifest[key] for key in ("protocol", "config_hash", "probe_hash", "model", "thinking", "max_tokens", "git_head", "implementation_sha256", "scientific_worktree_status_sha256")}
        mismatches = {key: {"expected": value, "found": manifest.get(key)} for key, value in compatibility.items() if manifest.get(key) != value}
        if mismatches:
            manifest.update(status="failed", failure=f"resume manifest incompatible: {mismatches}", finished_at_utc=_utc()); _atomic_json(manifest_path, manifest); await _close_backend(backend); return manifest
    else:
        manifest = base_manifest
        _atomic_json(manifest_path, manifest)  # durable provenance precedes credentials and provider calls
    by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events: by_id[str(event["logical_id"])].append(event)
    if any(sum(e.get("error") is None and e.get("parsed_answer") is not None for e in xs) > 1 for xs in by_id.values()):
        manifest.update(status="invalid_duplicate_success", finished_at_utc=_utc()); _atomic_json(manifest_path, manifest); await _close_backend(backend); return manifest
    prior_costs = [e.get("attempt_cost_usd") for e in events]
    held_reservations = sum(float(e.get("cost_reservation_held_usd") or 0.0) for e in events)
    physical, experiment_cost = len(events), sum(float(value) for value in prior_costs if value is not None)
    try:
        if events:
            prior_manifest_cost = manifest.get("observed_cost_usd")
            if prior_manifest_cost is None or not math.isclose(float(prior_manifest_cost), experiment_cost, rel_tol=0.0, abs_tol=1e-9):
                raise RuntimeError("prior manifest cost does not reconcile with raw events")
            if not math.isclose(float(manifest.get("held_cost_reservation_usd", 0.0)), held_reservations, rel_tol=0.0, abs_tol=1e-9): raise RuntimeError("prior manifest held reservation does not reconcile with raw events")
        _, ledger_row = _read_ledger(ledger, config["session_id"], config["global_cost_cap_usd"])
        if not math.isclose(float(ledger_row["ar001_spent_usd"]), experiment_cost, rel_tol=0.0, abs_tol=1e-9): raise RuntimeError("AR-001 ledger spent does not equal raw experiment cost")
        if not math.isclose(float(ledger_row["ar001_reserved_usd"]), held_reservations, rel_tol=0.0, abs_tol=1e-9): raise RuntimeError("AR-001 ledger reservation does not equal raw held reservations")
    except Exception as exc:
        manifest.update(status="failed", failure=f"resume reconciliation failed: {exc}", finished_at_utc=_utc()); _atomic_json(manifest_path, manifest); await _close_backend(backend); return manifest
    manifest.update(status="resuming" if events else "initialized", resumed_at_utc=_utc() if events else None)
    _atomic_json(manifest_path, manifest)
    try:
        if float(ledger_row["spent_usd"]) + float(ledger_row["reserved_usd"]) + config["hard_cost_cap_usd"] > config["global_cost_cap_usd"] + 1e-12:
            raise RuntimeError("prior cost plus experiment cap exceeds global cap")
        if backend is None:
            key = CredentialStore(config["credential_service"], config["credential_account"]).get(source=config["credential_source"])
            backend = DeepSeekDirectBackend(api_key=key, thinking="off", max_tokens=128)
        stop_status: str | None = None
        for task in tasks:
            for replicate in range(config["replicates"]):
                logical_id, prompt_hash, system_hash = _identity(config, config_hash, task, replicate); prior = by_id.get(logical_id, [])
                if any(e.get("error") is None and e.get("parsed_answer") is not None for e in prior): continue
                if len(prior) >= 2: continue
                if prior and (prior[-1].get("error_category") not in ALLOWED_RETRY_CATEGORIES or not prior[-1].get("retryable", False)): continue
                for attempt in range(len(prior), 2):
                    remaining = config["hard_cost_cap_usd"] - experiment_cost
                    reservation = config["max_attempt_cost_reserve_usd"]
                    if physical >= config["max_physical_attempts"] or remaining + 1e-12 < reservation: stop_status = "guard_stopped"; break
                    _ledger_change(ledger, config, reserve=reservation)
                    try:
                        response = await backend.complete(system_prompt=SYSTEM_PROMPT, user_prompt=prompt(task), model=config["model"], model_parameters={"thinking": "off", "max_tokens": 128})
                    except Exception as exc:
                        response = BackendResponse(raw_response=None, latency_s=0.0, error=f"backend exception: {type(exc).__name__}", error_category="transient_transport", retryable=True)
                    physical += 1; provider = response.provider_metadata or {}; provider_model = provider.get("model")
                    cost, cost_source = _attempt_cost(response, config)
                    if cost is None:
                        held_reservations += reservation; stop_status = "failed"; error = "missing provider cost and complete token usage"; category = "cost_accounting_missing"; parsed = None
                    else:
                        _ledger_change(ledger, config, reconcile_reserved=reservation, actual=cost); experiment_cost += cost
                        parsed = None; error, category = response.error, response.error_category
                        provider_returned = response.error is None or response.raw_response is not None or response.token_usage is not None or bool(provider)
                        if provider_returned and (provider_model is None or provider_model != config["model"]): error = f"provider model mismatch: {provider_model!r}"; category = "invalid_model"; stop_status = "invalid_model"
                        elif error is None:
                            try: parsed = parse_agent_output(response.raw_response or "")
                            except ResponseParseError as exc: error = f"ResponseParseError: {exc}"; category = "parse_error"
                    event = {"event": "completion", "protocol": config["protocol"], "logical_id": logical_id, "attempt": attempt, "replicate_id": replicate,
                             "task": task, "config_hash": config_hash, "probe_hash": config["probe_hash"], "prompt_hash": prompt_hash, "system_prompt_hash": system_hash,
                             "model": config["model"], "model_parameters": {"thinking": "off", "max_tokens": 128}, "provider_metadata": provider,
                             "raw_model_response": response.raw_response, "parsed_answer": None if parsed is None else parsed.answer, "confidence": None if parsed is None else parsed.confidence,
                             "answer_in_domain": None if parsed is None else parsed.answer_in_domain, "semantic_violation": None if parsed is None else parsed.semantic_violation,
                             "correct": bool(parsed and parsed.answer == task["correct_answer"]), "error": error, "error_category": category,
                             "retryable": response.retryable, "http_status": response.http_status, "latency_s": response.latency_s, "token_usage": response.token_usage, "attempt_cost_usd": cost, "cost_source": cost_source,
                             "cost_reservation_usd": reservation, "cost_reservation_held_usd": reservation if cost is None else 0.0, "retry_after_s": response.retry_after_s, "finished_at_utc": _utc()}
                    if cost is not None and cost > reservation + 1e-12: stop_status = "budget_violation"; event["budget_violation"] = "actual attempt cost exceeded frozen demonstrated reservation"
                    _append_event(events_path, event); events.append(event); by_id[logical_id].append(event)
                    if stop_status or error is None or category not in ALLOWED_RETRY_CATEGORIES or not response.retryable: break
                    delay = min(max(float(response.retry_after_s), 0.0), 30.0) if response.retry_after_s is not None else 0.05 + int(logical_id[:4], 16) % 20 / 100
                    await sleep(delay)
                if stop_status: break
            if stop_status: break
        successes = [e for e in events if e.get("error") is None and e.get("parsed_answer") is not None]
        unique_success = {e["logical_id"] for e in successes}
        status = stop_status or ("completed" if len(unique_success) == 168 else "guard_stopped" if physical >= config["max_physical_attempts"] or experiment_cost >= config["hard_cost_cap_usd"] else "incomplete")
        manifest.update(status=status, completed_logical_queries=len(unique_success), physical_attempts=physical, observed_cost_usd=experiment_cost, held_cost_reservation_usd=held_reservations, finished_at_utc=_utc())
    except Exception as exc:
        manifest.update(status="failed", failure=f"{type(exc).__name__}: {exc}", physical_attempts=physical, observed_cost_usd=experiment_cost, held_cost_reservation_usd=held_reservations, finished_at_utc=_utc())
    finally:
        await _close_backend(backend)
        _atomic_json(manifest_path, manifest)
    return manifest


async def run_real(path: str | Path = DEFAULT_CONFIG, *, confirm_real: bool = False, backend: Any = None,
                   output_dir: str | Path | None = None, ledger_path: str | Path | None = None,
                   sleep: Callable[[float], Awaitable[None]] = _default_sleep) -> dict[str, Any]:
    if not confirm_real: raise SystemExit("real inference requires --confirm-real")
    config, _ = _load_config(path); output = _path(config["output_dir"], output_dir); output.mkdir(parents=True, exist_ok=True)
    lock_handle = (output / ".execution.lock").open("a+")
    try:
        try: fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            await _close_backend(backend); raise RuntimeError("AR-001 output directory is already execution-locked")
        return await _run_real_locked(path, confirm_real=True, backend=backend, output_dir=output, ledger_path=ledger_path, sleep=sleep)
    finally:
        try: fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        finally: lock_handle.close()


def _pairwise(values: list[Any]) -> float | None:
    if len(values) < 2: return None
    return sum(values[i] == values[j] for i in range(len(values)) for j in range(i + 1, len(values))) / (len(values) * (len(values) - 1) / 2)


def report(path: str | Path = DEFAULT_CONFIG, *, output_dir: str | Path | None = None, report_dir: str | Path | None = None) -> dict[str, Any]:
    config, config_hash = _load_config(path); output = _path(config["output_dir"], output_dir); destination = _path(config["report_dir"], report_dir)
    events_path = output / "events.jsonl"; events = [json.loads(x) for x in events_path.read_text().splitlines() if x.strip()] if events_path.exists() else []
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events: grouped[event["logical_id"]].append(event)
    duplicates = sum(sum(e.get("error") is None and e.get("parsed_answer") is not None for e in xs) > 1 for xs in grouped.values())
    successful = [next(e for e in reversed(xs) if e.get("error") is None and e.get("parsed_answer") is not None) for xs in grouped.values() if any(e.get("error") is None and e.get("parsed_answer") is not None for e in xs)]
    by_world: dict[str, list[dict[str, Any]]] = defaultdict(list); by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in successful: by_world[event["task"]["world"]].append(event); by_task[event["task"]["task_id"]].append(event)
    agreements = [{"task_id": task_id, "replicates": len(xs), "exact_3way_answer_agreement": len(xs) == 3 and len({x["parsed_answer"] for x in xs}) == 1,
                   "pairwise_answer_agreement": _pairwise([x["parsed_answer"] for x in xs]), "exact_3way_correctness_agreement": len(xs) == 3 and len({x["correct"] for x in xs}) == 1,
                   "pairwise_correctness_agreement": _pairwise([x["correct"] for x in xs])} for task_id, xs in sorted(by_task.items())]
    correct_conf = [float(e["confidence"]) for e in successful if e["correct"]]; wrong_conf = [float(e["confidence"]) for e in successful if not e["correct"]]
    usage = summarize_usage([e.get("token_usage") for e in events], input_per_million_tokens=config["input_per_million_tokens"], cached_input_per_million_tokens=config["cached_input_per_million_tokens"], output_per_million_tokens=config["output_per_million_tokens"])
    latencies = [float(e["latency_s"]) for e in events]
    result = {"protocol": config["protocol"], "config_hash": config_hash, "health": "invalid_duplicate_success" if duplicates else "complete" if len(successful) == 168 else "incomplete",
              "physical_attempts": len(events), "deduplicated_logical_successes": len(successful), "duplicate_success_logicals": duplicates,
              "valid_response_accuracy": sum(e["correct"] for e in successful) / len(successful) if successful else None,
              "accuracy_by_world": {w: sum(e["correct"] for e in xs) / len(xs) for w, xs in sorted(by_world.items())},
              "semantic_ood": sum(e.get("semantic_violation") == "answer_out_of_domain" for e in successful),
              "technical_retries": sum(int(e.get("attempt", 0)) > 0 for e in events), "errors_by_category": {k: sum(e.get("error_category") == k for e in events) for k in sorted({e.get("error_category") for e in events if e.get("error_category")})},
              "latency_s": {"mean": statistics.fmean(latencies) if latencies else None, "median": statistics.median(latencies) if latencies else None,
                            "min": min(latencies) if latencies else None, "max": max(latencies) if latencies else None, "total": sum(latencies)},
              "usage": usage, "cost_accounting_complete": all(e.get("attempt_cost_usd") is not None for e in events), "observed_cost_usd": sum(float(e["attempt_cost_usd"]) for e in events if e.get("attempt_cost_usd") is not None),
              "provider_models": sorted({str((e.get("provider_metadata") or {}).get("model")) for e in events}), "provider_fingerprints": sorted({str((e.get("provider_metadata") or {}).get("system_fingerprint")) for e in events if (e.get("provider_metadata") or {}).get("system_fingerprint")}),
              "agreement": {"tasks": agreements, "mean_pairwise_answer": sum(x["pairwise_answer_agreement"] for x in agreements if x["pairwise_answer_agreement"] is not None) / sum(x["pairwise_answer_agreement"] is not None for x in agreements) if any(x["pairwise_answer_agreement"] is not None for x in agreements) else None,
                            "mean_pairwise_correctness": sum(x["pairwise_correctness_agreement"] for x in agreements if x["pairwise_correctness_agreement"] is not None) / sum(x["pairwise_correctness_agreement"] is not None for x in agreements) if any(x["pairwise_correctness_agreement"] is not None for x in agreements) else None,
                            "exact_three_way_answer_rate": sum(x["exact_3way_answer_agreement"] for x in agreements) / len(agreements) if agreements else None,
                            "exact_three_way_correctness_rate": sum(x["exact_3way_correctness_agreement"] for x in agreements) / len(agreements) if agreements else None},
              "confidence_correctness": {"mean_correct": sum(correct_conf) / len(correct_conf) if correct_conf else None, "mean_incorrect": sum(wrong_conf) / len(wrong_conf) if wrong_conf else None}}
    _atomic_json(destination / "report.json", result); return result


def main() -> None:
    parser = argparse.ArgumentParser(description="AR-001 explicit-rule execution diagnostic")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG)); parser.add_argument("--preflight", action="store_true"); parser.add_argument("--run", action="store_true"); parser.add_argument("--confirm-real", action="store_true"); parser.add_argument("--report", action="store_true")
    args = parser.parse_args(); result = report(args.config) if args.report else asyncio.run(run_real(args.config, confirm_real=args.confirm_real)) if args.run else preflight(args.config); print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__": main()
