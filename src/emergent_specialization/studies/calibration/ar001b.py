"""AR-001B: explicit full-2D GF(7) execution control.

The probe manifest is generated once and then frozen.  This module is a small
single-agent diagnostic; it never invokes the society runner.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import fcntl
import hashlib
import json
import math
import random
import tempfile
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from emergent_specialization.core.costs import estimate_usage_cost, summarize_usage
from emergent_specialization.providers.credentials import CredentialStore
from emergent_specialization.core.environment import HIDDEN_RULES, HiddenWorldEnvironment
from emergent_specialization.studies.calibration.explicit_rule_execution import _atomic_json, _append_event
from emergent_specialization.core.models import BackendResponse
from emergent_specialization.core.parsing import ResponseParseError, parse_agent_output
from emergent_specialization.providers import DeepSeekDirectBackend

ROOT = Path(__file__).resolve().parents[4]
CONFIG_PATH = ROOT / "configs/research/auto/ar001b_full_2d.yaml"
PROBE_PATH = ROOT / "data/calibrations/ar001b-full-2d/probe_set.json"
OUTPUT_DIR = ROOT / "data/auto-research/ar001b-full-2d"
REPORT_DIR = ROOT / "reports/auto-research/ar001b-full-2d"
LEDGER_PATH = ROOT / "reports/auto-research/cost_ledger.csv"
MODEL = "deepseek-v4-flash"
PROBE_HASH: str | None = None
INPUT_PRICE = 0.14
CACHED_INPUT_PRICE = 0.0028
OUTPUT_PRICE = 0.28
RESERVATION = 0.005
HARD_CAP = 0.05
SESSION_ID = "autonomous-session-2026-08-08"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def expected(world: str, x: int, y: int) -> int:
    a, b, c = HIDDEN_RULES[world]
    return (a * x + b * y + c) % 7


def generate_probes() -> list[dict[str, Any]]:
    old = json.loads((ROOT / "data/probe_set.json").read_text(encoding="utf-8"))["tasks"]
    old_pairs = {(int(item["x"]), int(item["y"])) for item in old}
    env = HiddenWorldEnvironment()
    tasks: list[dict[str, Any]] = []
    for world_index, world in enumerate(env.worlds):
        rng = random.Random(0xA001B + world_index * 997)
        pairs = [(x, y) for x in range(env.x_min, env.x_max + 1) for y in range(env.x_min, env.x_max + 1)
                 if (x, y) not in old_pairs and x != 0 and y != 0]
        rng.shuffle(pairs)
        by_label: dict[int, list[tuple[int, int]]] = {label: [] for label in range(7)}
        for x, y in pairs:
            label = expected(world, x, y)
            if len(by_label[label]) < 2:
                by_label[label].append((x, y))
            if all(len(items) == 2 for items in by_label.values()):
                break
        if any(len(items) != 2 for items in by_label.values()):
            raise RuntimeError(f"unable to balance AR-001B probes for {world}")
        for label in range(7):
            for x, y in by_label[label]:
                tasks.append({"world": world, "x": x, "y": y, "correct_answer": label,
                              "task_id": f"ar001b-{world}-{len(tasks)}"})
    if len(tasks) != 56 or len({(x["world"], x["x"], x["y"]) for x in tasks}) != len(tasks):
        raise RuntimeError("AR-001B duplicate/count invariant failed")
    if any(sum(item["world"] == world and item["correct_answer"] == label for item in tasks) != 2
           for world in env.worlds for label in range(7)):
        raise RuntimeError("AR-001B label balance invariant failed")
    if sum(item["x"] != 0 and item["y"] != 0 for item in tasks) < 48:
        raise RuntimeError("AR-001B nonzero-coordinate invariant failed")
    if any((item["x"], item["y"]) in old_pairs for item in tasks):
        raise RuntimeError("AR-001B reused an old probe pair")
    return tasks


def freeze_probes() -> dict[str, Any]:
    tasks = generate_probes()
    payload = {"protocol": "AR-001B-FULL-2D-EXECUTION", "tasks": tasks,
               "probe_hash": _hash(tasks), "old_probe_pairs_excluded": True}
    PROBE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _atomic_json(PROBE_PATH, payload)
    return payload


def load_probes() -> list[dict[str, Any]]:
    payload = json.loads(PROBE_PATH.read_text(encoding="utf-8"))
    tasks = payload["tasks"]
    if payload.get("probe_hash") != _hash(tasks) or len(tasks) != 56:
        raise ValueError("AR-001B probe hash/count mismatch")
    if any(expected(t["world"], int(t["x"]), int(t["y"])) != t["correct_answer"] for t in tasks):
        raise ValueError("AR-001B ground-truth mismatch")
    return tasks


def user_prompt(task: dict[str, Any]) -> str:
    a, b, c = HIDDEN_RULES[str(task["world"])]
    return (f"This is an isolated arithmetic diagnostic. The local rule is explicitly "
            f"z=({a}*x+{b}*y+{c}) mod 7. For x={task['x']} and y={task['y']}, compute z.\n"
            'Return only JSON: {"answer": <integer 0..6>, "confidence": <number 0..1>}.')


def _read_ledger() -> tuple[list[dict[str, str]], dict[str, str]]:
    with LEDGER_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle); rows = list(reader); fields = set(reader.fieldnames or [])
    required = {"session_id", "global_budget_usd", "spent_usd", "reserved_usd", "status", "updated_at_utc"}
    if not required <= fields:
        raise RuntimeError("global ledger schema is incomplete")
    matches = [row for row in rows if row.get("session_id") == SESSION_ID]
    if len(matches) != 1 or matches[0].get("status") != "open":
        raise RuntimeError("AR-001B session ledger row missing or closed")
    return rows, matches[0]


def _write_ledger(rows: list[dict[str, str]]) -> None:
    fields = ["session_id", "global_budget_usd", "spent_usd", "reserved_usd", "status", "updated_at_utc"]
    fields += sorted({key for row in rows for key in row} - set(fields))
    fd, name = tempfile.mkstemp(prefix=".cost-ledger.", dir=LEDGER_PATH.parent)
    try:
        with open(fd, "w", newline="", encoding="utf-8", closefd=True) as handle:
            writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows); handle.flush()
        Path(name).replace(LEDGER_PATH)
    finally:
        if Path(name).exists(): Path(name).unlink()


def _ledger_delta(*, reserve: float = 0.0, release: float = 0.0, actual: float = 0.0) -> None:
    lock_path = LEDGER_PATH.with_suffix(".csv.lock")
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        rows, row = _read_ledger()
        spent, reserved = float(row["spent_usd"]), float(row["reserved_usd"])
        if release and reserved + 1e-12 < release:
            raise RuntimeError("AR-001B ledger reservation mismatch")
        reserved = reserved - release + reserve
        spent += actual
        if spent + reserved > 2.0 + 1e-12:
            raise RuntimeError("global budget guard")
        row.update(spent_usd=f"{spent:.9f}", reserved_usd=f"{reserved:.9f}", updated_at_utc=_now())
        _write_ledger(rows)


def _cost(response: BackendResponse) -> float | None:
    if response.observed_cost_usd is not None:
        value = float(response.observed_cost_usd)
        return value if math.isfinite(value) and value >= 0 else None
    return estimate_usage_cost(response.token_usage, input_per_million_tokens=INPUT_PRICE,
                               cached_input_per_million_tokens=CACHED_INPUT_PRICE,
                               output_per_million_tokens=OUTPUT_PRICE)


async def _close(backend: Any) -> None:
    close = getattr(backend, "close", None)
    if callable(close):
        result = close()
        if hasattr(result, "__await__"):
            await result


async def run(confirm_real: bool = False) -> dict[str, Any]:
    if not confirm_real:
        raise SystemExit("AR-001B real inference requires --confirm-real")
    tasks = load_probes(); OUTPUT_DIR.mkdir(parents=True, exist_ok=True); REPORT_DIR.mkdir(parents=True, exist_ok=True)
    events_path = OUTPUT_DIR / "events.jsonl"; manifest_path = OUTPUT_DIR / "manifest.json"
    if events_path.exists() or manifest_path.exists():
        raise RuntimeError("AR-001B output already exists; no duplicate run is allowed")
    manifest = {"protocol": "AR-001B-FULL-2D-EXECUTION", "status": "initialized", "model": MODEL,
                "logical_calls": 112, "max_physical_attempts": 224, "probe_hash": _hash(tasks),
                "created_at_utc": _now(), "thinking": "off", "hard_cost_cap_usd": HARD_CAP}
    _atomic_json(manifest_path, manifest)
    backend = None; events: list[dict[str, Any]] = []; cost_total = 0.0; physical = 0; retries = 0
    try:
        key = CredentialStore().get(source="keychain")
        backend = DeepSeekDirectBackend(api_key=key, thinking="off", max_tokens=128)
        for task in tasks:
            for replicate in range(2):
                logical_id = _hash({"task": task, "replicate": replicate, "probe_hash": _hash(tasks), "model": MODEL})
                for attempt in range(2):
                    if physical >= 224 or cost_total + RESERVATION > HARD_CAP + 1e-12:
                        raise RuntimeError("AR-001B budget/attempt guard")
                    _ledger_delta(reserve=RESERVATION); reserved = RESERVATION
                    response = await backend.complete(system_prompt="Execute the supplied arithmetic rule; return only the requested JSON.",
                                                      user_prompt=user_prompt(task), model=MODEL,
                                                      model_parameters={"thinking": "off", "max_tokens": 128})
                    physical += 1
                    value = _cost(response)
                    parsed = None; confidence = None; error = response.error; category = response.error_category
                    if value is None:
                        # Keep the reservation: an unpriced attempt is terminal.
                        event = {"logical_id": logical_id, "attempt": attempt, "task": task, "replicate": replicate,
                                 "error": "cost_accounting_missing", "error_category": "cost_accounting_missing",
                                 "retryable": False, "latency_s": response.latency_s, "token_usage": response.token_usage,
                                 "provider_metadata": response.provider_metadata or {}, "attempt_cost_usd": None}
                        _append_event(events_path, event); events.append(event); raise RuntimeError("AR-001B cost accounting missing")
                    _ledger_delta(release=reserved, actual=float(value)); cost_total += float(value)
                    provider = response.provider_metadata or {}
                    if provider.get("model") != MODEL:
                        error = f"provider model mismatch: {provider.get('model')!r}"; category = "invalid_model"
                    elif error is None:
                        try:
                            parsed_response = parse_agent_output(response.raw_response or "")
                            parsed, confidence = parsed_response.answer, parsed_response.confidence
                        except ResponseParseError as exc:
                            error = f"ResponseParseError: {exc}"; category = "parse_error"
                    event = {"logical_id": logical_id, "attempt": attempt, "task": task, "replicate": replicate,
                             "raw_model_response": response.raw_response, "parsed_answer": parsed, "confidence": confidence,
                             "correct": parsed == task["correct_answer"] if parsed is not None else False,
                             "error": error, "error_category": category, "retryable": response.retryable,
                             "latency_s": response.latency_s, "token_usage": response.token_usage,
                             "provider_metadata": provider, "attempt_cost_usd": float(value), "finished_at_utc": _now()}
                    _append_event(events_path, event); events.append(event)
                    if error is None:
                        break
                    if category not in {"parse_error", "empty_content", "transient_transport", "transport"} or not response.retryable:
                        raise RuntimeError(error)
                    retries += 1
                else:
                    raise RuntimeError("AR-001B retry exhaustion")
        successes = [e for e in events if e.get("error") is None and e.get("parsed_answer") is not None]
        manifest.update(status="completed", completed_logical_queries=len(successes), physical_attempts=physical,
                        retries=retries, observed_cost_usd=cost_total, finished_at_utc=_now())
    except Exception as exc:
        manifest.update(status="failed", failure=f"{type(exc).__name__}: {exc}", physical_attempts=physical,
                        retries=retries, observed_cost_usd=cost_total, finished_at_utc=_now())
    finally:
        await _close(backend)
        _atomic_json(manifest_path, manifest)
    return manifest


def report() -> dict[str, Any]:
    tasks = load_probes(); events_path = OUTPUT_DIR / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_text().splitlines() if line.strip()] if events_path.exists() else []
    valid = [e for e in events if e.get("error") is None and e.get("parsed_answer") is not None]
    result = {"protocol": "AR-001B-FULL-2D-EXECUTION", "logical_successes": len(valid),
              "physical_attempts": len(events), "accuracy": sum(e["correct"] for e in valid) / len(valid) if valid else None,
              "errors": sum(e.get("error") is not None for e in events), "retries": sum(e.get("attempt", 0) > 0 for e in events),
              "usage": summarize_usage([e.get("token_usage") for e in events], input_per_million_tokens=INPUT_PRICE,
                                        cached_input_per_million_tokens=CACHED_INPUT_PRICE, output_per_million_tokens=OUTPUT_PRICE),
              "observed_cost_usd": sum(float(e.get("attempt_cost_usd") or 0) for e in events),
              "probe_hash": _hash(tasks), "x_nonzero": sum(t["x"] != 0 for t in tasks), "y_nonzero": sum(t["y"] != 0 for t in tasks)}
    _atomic_json(REPORT_DIR / "report.json", result); return result


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--generate-probes", action="store_true"); parser.add_argument("--run", action="store_true"); parser.add_argument("--confirm-real", action="store_true"); parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    if args.generate_probes: print(json.dumps(freeze_probes(), indent=2, sort_keys=True)); return
    result = report() if args.report else asyncio.run(run(args.confirm_real)) if args.run else {"probe_hash": _hash(load_probes()), "tasks": len(load_probes())}
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
