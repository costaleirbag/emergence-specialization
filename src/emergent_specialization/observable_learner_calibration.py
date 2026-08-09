"""OBSERVABLE ECOLOGY LEARNER CALIBRATION V1.

This module is deliberately separate from the society runtime.  It freezes a
small, single-agent Direct-DeepSeek calibration of the V3.1 observable ecology,
then runs/analyzes exactly the frozen logical contexts.  No router, shared
memory, or adaptive selection is used here.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import fcntl
import itertools
import json
import math
import os
import statistics
import subprocess
import tempfile
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .credentials import CredentialStore
from .ecological_information import FAMILIES, GEOMETRIES, all_symbolic_cases, generate_environment, sample_history, solve
from .ecological_information_v31 import (
    EVAL_TEMPLATE_IDS,
    TRAIN_TEMPLATE_IDS,
    observable_o,
    render_observable,
)
from .models import BackendResponse
from .providers import DeepSeekDirectBackend

ROOT = Path(__file__).resolve().parents[2]
REPORT_ROOT = ROOT / "reports/task-ecology/observable-learner-calibration-v1"
DATA_ROOT = ROOT / "data/auto-research/observable-learner-calibration-v1"
V31_ROOT = ROOT / "reports/task-ecology/ecological-information-v31"
MODEL = "deepseek-v4-flash"
PROTOCOL = "OBSERVABLE-ECOLOGY-LEARNER-CALIBRATION-V1"
SEEDS = (9201, 9202, 9203, 9204)
H = 8
PROBE_COUNT = 6
MAX_ATTEMPTS = 2
HARD_CAP_USD = 0.20
RESERVATION_USD = 0.00025
INPUT_PRICE = 0.14
CACHED_INPUT_PRICE = 0.0028
OUTPUT_PRICE = 0.28
SYSTEM_PROMPT = (
    "You are a single-agent decision learner. Use resolved cases only as "
    "feedback-only memory. Return only the requested JSON object."
)
OUTPUT_INSTRUCTION = 'Return only JSON: {"decisions":[0,1,0]}. The array must contain exactly three binary decisions in order.'
RETRYABLE = {"parse_error", "empty_content", "transient_transport", "transport", "rate_limit", "server_error", "overloaded"}


def now() -> str:
    return datetime.now(UTC).isoformat()


def stable_hash(value: Any) -> str:
    import hashlib
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush(); os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def _case_record(family: str, x: tuple[int, int, int], y: tuple[int, int, int], template_id: int, *, role: str) -> dict[str, Any]:
    return {"case_id": f"{family}:{role}:t{template_id}:{''.join(map(str, x))}", "family": family,
            "x": list(x), "y": list(y), "template_id": template_id, "role": role}


def _history_for(geometry: str, seed: int, source: str) -> list[dict[str, Any]]:
    env = generate_environment(geometry, seed)
    rng = __import__("random").Random(0x31A7 + seed * 1009 + sum(map(ord, source)) * 17)
    cases = sample_history(env, source, H, rng)
    return [_case_record(source, case.x, case.y, TRAIN_TEMPLATE_IDS[i % len(TRAIN_TEMPLATE_IDS)], role="memory")
            for i, case in enumerate(cases)]


def _probe_candidates(geometry: str, seed: int, histories: dict[str, list[dict[str, Any]]], target: str) -> list[dict[str, Any]]:
    env = generate_environment(geometry, seed)
    excluded = {tuple(item["x"]) for values in histories.values() for item in values}
    candidates = []
    for item in all_symbolic_cases(target):
        x = tuple(item.x)
        if x in excluded:
            continue
        y = solve(env.theta_by_family[target], x)
        candidates.append((x, y))
    # Choose the lexicographically first valid six-case set.  The balance
    # constraint is fixed before inference and is independent of model output.
    for combo in itertools.combinations(candidates, PROBE_COUNT):
        if all(sum(y[j] for _, y in combo) == PROBE_COUNT // 2 for j in range(3)):
            return [_case_record(target, x, y, EVAL_TEMPLATE_IDS[0], role="probe") for x, y in combo]
    raise RuntimeError(f"unable to construct balanced held-out probes: {geometry}/{seed}/{target}")


def _render_case(record: dict[str, Any]) -> str:
    family = str(record["family"])
    o = observable_o(family, tuple(record["x"]))
    return render_observable(o, family, int(record["template_id"]))


def render_user(task: dict[str, Any]) -> str:
    memory = task.get("memory") or []
    pieces: list[str] = []
    if memory:
        pieces.append("Prior resolved cases:\n" + "\n\n".join(
            _render_case(item) + f"\nResolved decision: {json.dumps(item['y'], separators=(',', ':'))}" for item in memory
        ))
    pieces.append("CURRENT CASE:\n" + _render_case(task["probe"]))
    pieces.append(OUTPUT_INSTRUCTION)
    return "\n\n".join(pieces)


def _load_lstar() -> dict[tuple[str, str, str], dict[str, float]]:
    path = V31_ROOT / "observable_Lstar_natural.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    selected = {}
    for row in rows:
        if int(row["h"]) == H and row.get("policy", "natural") == "natural":
            key = (row["geometry"], row["source"], row["target"])
            selected[key] = {"L_star": float(row["L_star"]), "A_star": float(row["A_star"])}
    if len(selected) != len(GEOMETRIES) * len(FAMILIES) * len(FAMILIES):
        raise RuntimeError("V3.1 observable Lstar table is incomplete")
    jpath = V31_ROOT / "observable_J_natural.csv"
    with jpath.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if int(row["h"]) == H and row.get("policy", "natural") == "natural":
                selected[(row["geometry"], row["source"], row["target"])] ["J_obs"] = float(row["J_normalized"])
    if any("J_obs" not in value for value in selected.values()):
        raise RuntimeError("V3.1 observable J table is incomplete")
    return selected


def build_tasks() -> list[dict[str, Any]]:
    lstar = _load_lstar()
    tasks: list[dict[str, Any]] = []
    for geometry in GEOMETRIES:
        for seed in SEEDS:
            histories = {source: _history_for(geometry, seed, source) for source in FAMILIES}
            probes = {target: _probe_candidates(geometry, seed, histories, target) for target in FAMILIES}
            for target in FAMILIES:
                for probe in probes[target]:
                    task = {"condition": "baseline", "geometry": geometry, "seed": seed, "source": None,
                            "target": target, "probe": probe, "memory": [], "h": 0}
                    task.update(lstar[(geometry, target, target)])
                    task["prompt_hash"] = stable_hash({"system": SYSTEM_PROMPT, "user": render_user(task)})
                    tasks.append(task)
            for source in FAMILIES:
                for target in FAMILIES:
                    for probe in probes[target]:
                        task = {"condition": "transfer", "geometry": geometry, "seed": seed, "source": source,
                                "target": target, "probe": probe, "memory": histories[source], "h": H}
                        task.update(lstar[(geometry, source, target)])
                        task["prompt_hash"] = stable_hash({"system": SYSTEM_PROMPT, "user": render_user(task)})
                        tasks.append(task)
    return tasks


def expected_calls() -> dict[str, int]:
    baseline = len(GEOMETRIES) * len(SEEDS) * len(FAMILIES) * PROBE_COUNT
    transfer = len(GEOMETRIES) * len(SEEDS) * len(FAMILIES) * len(FAMILIES) * PROBE_COUNT
    return {"baseline": baseline, "transfer": transfer, "total": baseline + transfer}


def verify_v31() -> dict[str, Any]:
    gate_path = V31_ROOT / "gate_summary.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8")) if gate_path.exists() else {}
    audit_path = V31_ROOT / "observation_channel_audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else {}
    checks = {
        "all_gates_pass": bool(gate.get("all_pass")),
        "zero_observation_loss": all(float(gate.get("observation_loss", {}).get(k, 1)) == 0.0 for k in ("MAE_J", "MAX_J", "MAE_Lstar", "MAX_Lstar")),
        "renderer_collision_count_zero": int(audit.get("renderer_collision_count", -1)) == 0,
        "theta_leakage_count_zero": int(audit.get("theta_leakage_count", -1)) == 0,
        "family_recovery_100": float(audit.get("new_family_recovery_percent", 0)) == 100.0,
        "latent_prior_unchanged": bool(audit.get("latent_prior_unchanged")),
        "nested_history_test_available": (ROOT / "tests/test_ecological_information_v31.py").exists(),
        "J_obs_file": (V31_ROOT / "observable_J_natural.csv").exists(),
        "Lstar_file": (V31_ROOT / "observable_Lstar_natural.csv").exists(),
    }
    return {"checks": checks, "all_pass": all(checks.values()), "gate": gate, "audit": audit}


def _recent_cost_stats() -> dict[str, float]:
    costs: list[float] = []; prompt_tokens: list[float] = []; output_tokens: list[float] = []
    for path in (ROOT / "data/auto-research/ecology-transfer-qualification-v1").glob("*/events.jsonl"):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                try: event = json.loads(line)
                except json.JSONDecodeError: continue
                usage = event.get("token_usage") or {}
                if event.get("attempt_cost_usd") is not None:
                    costs.append(float(event["attempt_cost_usd"]))
                if usage.get("prompt_tokens") is not None: prompt_tokens.append(float(usage["prompt_tokens"]))
                if usage.get("completion_tokens") is not None: output_tokens.append(float(usage["completion_tokens"]))
    return {"mean_cost": statistics.mean(costs) if costs else 0.0,
            "mean_prompt_tokens": statistics.mean(prompt_tokens) if prompt_tokens else 0.0,
            "mean_output_tokens": statistics.mean(output_tokens) if output_tokens else 0.0,
            "n": float(len(costs))}


def cost_forecast(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    stats = _recent_cost_stats()
    # DeepSeek's recent semantic calls provide an empirical token/price anchor;
    # rendered prompt lengths are measured exactly and tokenized conservatively
    # at four characters/token for a pre-call budget forecast.
    prompt_tokens = [(len(SYSTEM_PROMPT) + len(render_user(task))) / 4.0 for task in tasks]
    output_tokens = [max(8.0, stats["mean_output_tokens"] or 16.0) for _ in tasks]
    estimated = sum((p * INPUT_PRICE + o * OUTPUT_PRICE) / 1_000_000 for p, o in zip(prompt_tokens, output_tokens))
    # Include the observed semantic-call mean as a cross-check, not as a reason
    # to hide a higher rendered-prompt estimate.
    observed_call_forecast = stats["mean_cost"] * len(tasks) if stats["n"] else estimated
    forecast = max(estimated, observed_call_forecast)
    result = {"logical_calls": len(tasks), "min_prompt_chars": min(map(lambda t: len(render_user(t)), tasks)),
              "max_prompt_chars": max(map(lambda t: len(render_user(t)), tasks)),
              "mean_prompt_chars": statistics.mean(len(render_user(t)) for t in tasks),
              "estimated_from_rendered_prompts_usd": estimated,
              "recent_semantic_call_forecast_usd": observed_call_forecast,
              "projected_nominal_usd": forecast,
              "safety_margin_50pct_usd": forecast * 1.5,
              "hard_cap_usd": HARD_CAP_USD, "recent_stats": stats,
              "within_cap_with_margin": forecast * 1.5 <= HARD_CAP_USD}
    return result


def freeze_manifest() -> dict[str, Any]:
    verification = verify_v31()
    if not verification["all_pass"]:
        raise RuntimeError(f"V3.1 precondition failed: {verification['checks']}")
    tasks = build_tasks()
    expected = expected_calls()
    counts = {key: sum(task["condition"] == key for task in tasks) for key in ("baseline", "transfer")}
    if counts != {"baseline": expected["baseline"], "transfer": expected["transfer"]} or len(tasks) != expected["total"]:
        raise RuntimeError(f"task count mismatch: {counts}, {len(tasks)}, expected {expected}")
    forecast = cost_forecast(tasks)
    if not forecast["within_cap_with_margin"]:
        raise RuntimeError(f"cost forecast exceeds cap with safety margin: {forecast}")
    try: git_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception: git_head = "unknown"
    manifest = {"protocol": PROTOCOL, "created_at_utc": now(), "git_head": git_head,
                "model": MODEL, "provider": "deepseek_direct", "thinking": "off", "h": H,
                "seeds": list(SEEDS), "geometries": list(GEOMETRIES), "families": list(FAMILIES),
                "probe_count": PROBE_COUNT, "logical_calls": expected["total"], "call_breakdown": expected,
                "hard_cap_usd": HARD_CAP_USD, "max_attempts_per_logical": MAX_ATTEMPTS,
                "v31_gate_verification": verification, "cost_forecast": forecast,
                "lstar_source": str(V31_ROOT / "observable_Lstar_natural.csv"),
                "j_source": str(V31_ROOT / "observable_J_natural.csv"), "tasks": tasks}
    manifest["tasks_hash"] = stable_hash(tasks)
    path = REPORT_ROOT / "manifest.json"
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("tasks_hash") != manifest["tasks_hash"]:
            raise RuntimeError("frozen learner manifest exists with a different task hash")
        return existing
    atomic_json(path, manifest)
    return manifest


def _parse_json_objects(raw: str) -> list[Any]:
    candidates: list[Any] = []
    try: candidates.append(json.loads(raw))
    except json.JSONDecodeError: pass
    for start, char in enumerate(raw):
        if char != "{": continue
        depth = 0; in_string = False; escape = False
        for index in range(start, len(raw)):
            current = raw[index]
            if in_string:
                if escape: escape = False
                elif current == "\\": escape = True
                elif current == '"': in_string = False
                continue
            if current == '"': in_string = True
            elif current == "{": depth += 1
            elif current == "}":
                depth -= 1
                if depth == 0:
                    try: candidates.append(json.loads(raw[start:index + 1]))
                    except json.JSONDecodeError: pass
                    break
    return candidates


def parse_decisions(raw: str | None) -> tuple[list[int] | None, str | None]:
    if not isinstance(raw, str) or not raw.strip():
        return None, "empty_content"
    objects = _parse_json_objects(raw)
    for obj in reversed(objects):
        if not isinstance(obj, dict) or "decisions" not in obj:
            continue
        value = obj["decisions"]
        if isinstance(value, list) and len(value) == 3 and all(isinstance(bit, int) and bit in (0, 1) and not isinstance(bit, bool) for bit in value):
            return list(value), None
        return None, "out_of_domain"
    return None, "parse_error"


def _cost(response: BackendResponse) -> float | None:
    from .costs import estimate_usage_cost
    if response.observed_cost_usd is not None:
        value = float(response.observed_cost_usd)
        return value if math.isfinite(value) and value >= 0 else None
    return estimate_usage_cost(response.token_usage, input_per_million_tokens=INPUT_PRICE,
                               cached_input_per_million_tokens=CACHED_INPUT_PRICE, output_per_million_tokens=OUTPUT_PRICE)


def _budget_path() -> Path:
    return DATA_ROOT / "campaign_budget.json"


def _budget_change(*, reserve: float = 0.0, release: float = 0.0, actual: float = 0.0) -> dict[str, Any]:
    path = _budget_path(); lock_path = path.with_suffix(".lock"); path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        budget = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"protocol": PROTOCOL, "hard_cap_usd": HARD_CAP_USD, "spent_usd": 0.0, "reserved_usd": 0.0, "history": []}
        spent = float(budget.get("spent_usd", 0.0)); held = float(budget.get("reserved_usd", 0.0))
        if held + 1e-12 < release or spent + held - release + reserve + actual > HARD_CAP_USD + 1e-12:
            raise RuntimeError("observable learner hard budget guard")
        budget["reserved_usd"] = held - release + reserve; budget["spent_usd"] = spent + actual; budget["updated_at_utc"] = now()
        atomic_json(path, budget)
        return budget


def _load_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists(): return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _append_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n"); handle.flush(); os.fsync(handle.fileno())


async def run_real(*, confirm_real: bool = False) -> dict[str, Any]:
    if not confirm_real:
        raise SystemExit("real learner calibration requires --confirm-real")
    manifest_path = REPORT_ROOT / "manifest.json"
    if not manifest_path.exists(): raise RuntimeError("freeze manifest before real execution")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("logical_calls") != expected_calls()["total"] or manifest.get("tasks_hash") != stable_hash(manifest["tasks"]):
        raise RuntimeError("frozen learner manifest integrity failure")
    output = DATA_ROOT; events_path = output / "events.jsonl"; status_path = output / "run_status.json"
    events = _load_events(events_path)
    completed = {str(event["logical_id"]) for event in events if event.get("terminal")}
    attempts: dict[str, int] = defaultdict(int)
    for event in events: attempts[str(event.get("logical_id"))] = max(attempts[str(event.get("logical_id"))], int(event.get("attempt", 0)) + 1)
    status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {"protocol": PROTOCOL, "status": "initialized", "tasks_hash": manifest["tasks_hash"], "logical_calls": manifest["logical_calls"], "created_at_utc": now()}
    if status.get("tasks_hash") != manifest["tasks_hash"]: raise RuntimeError("existing learner output has a different manifest")
    status.update(status="running", started_or_resumed_at_utc=now()); atomic_json(status_path, status)
    backend = None; retries = sum(int(event.get("attempt", 0)) for event in events); cost_total = sum(float(event.get("attempt_cost_usd") or 0) for event in events)
    try:
        key = CredentialStore().get(source="keychain")
        backend = DeepSeekDirectBackend(api_key=key, thinking="off", max_tokens=32)
        for task in manifest["tasks"]:
            logical_id = stable_hash({"protocol": PROTOCOL, "tasks_hash": manifest["tasks_hash"], "task": task})
            if logical_id in completed: continue
            start = attempts.get(logical_id, 0)
            if start >= MAX_ATTEMPTS: raise RuntimeError(f"retry exhaustion for {logical_id}")
            for attempt in range(start, MAX_ATTEMPTS):
                _budget_change(reserve=RESERVATION_USD)
                response: BackendResponse
                try:
                    response = await backend.complete(system_prompt=SYSTEM_PROMPT, user_prompt=render_user(task), model=MODEL,
                                                      model_parameters={"thinking": "off", "max_tokens": 32})
                finally:
                    pass
                cost = _cost(response)
                if cost is None:
                    _budget_change(release=RESERVATION_USD)
                    raise RuntimeError("cost accounting unavailable; stopped")
                _budget_change(release=RESERVATION_USD, actual=float(cost)); cost_total += float(cost)
                decisions, parse_category = parse_decisions(response.raw_response)
                provider = response.provider_metadata or {}
                if provider.get("model") != MODEL:
                    raise RuntimeError(f"provider model mismatch: {provider.get('model')!r}")
                category = response.error_category or parse_category
                error = response.error or parse_category
                expected = task["probe"]["y"]
                terminal = category == "out_of_domain" or (error is None and decisions is not None)
                event = {"protocol": PROTOCOL, "logical_id": logical_id, "attempt": attempt, "task": task,
                         "decisions": decisions, "expected": expected, "correct": decisions == expected if decisions is not None else False,
                         "error": error, "error_category": category, "terminal": terminal,
                         "raw_model_response": response.raw_response, "latency_s": response.latency_s,
                         "token_usage": response.token_usage, "provider_metadata": provider,
                         "attempt_cost_usd": float(cost), "finished_at_utc": now()}
                _append_event(events_path, event); events.append(event)
                if terminal:
                    completed.add(logical_id); break
                if not response.retryable or category not in RETRYABLE:
                    raise RuntimeError(f"non-retryable learner response: {category}")
                retries += 1
            else: raise RuntimeError(f"retry exhaustion for {logical_id}")
        if len(completed) != manifest["logical_calls"]: raise RuntimeError(f"logical coverage {len(completed)}/{manifest['logical_calls']}")
        status.update(status="completed", physical_attempts=len(events), retries=retries, observed_cost_usd=cost_total, finished_at_utc=now())
    except Exception as exc:
        status.update(status="incomplete", failure=f"{type(exc).__name__}: {exc}", physical_attempts=len(events), retries=retries, observed_cost_usd=cost_total, finished_at_utc=now())
    finally:
        if backend is not None: await backend.close()
        atomic_json(status_path, status)
    return status


def _terminal_events(manifest: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events: by_id[str(event["logical_id"])].append(event)
    out = {}
    for task in manifest["tasks"]:
        logical_id = stable_hash({"protocol": PROTOCOL, "tasks_hash": manifest["tasks_hash"], "task": task})
        candidates = by_id.get(logical_id, [])
        terminal = [event for event in candidates if event.get("terminal")]
        if terminal: out[logical_id] = terminal[-1]
    return out


def _matrix(rows: list[dict[str, Any]], field: str) -> np.ndarray:
    index = {family: i for i, family in enumerate(FAMILIES)}; result = np.zeros((4, 4), dtype=float)
    for row in rows: result[index[row["source"]], index[row["target"]]] = float(row[field])
    return result


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    den = float(np.linalg.norm(a) * np.linalg.norm(b)); return float(np.sum(a * b) / den) if den else 0.0


def _centered(a: np.ndarray) -> np.ndarray:
    p = np.eye(a.shape[0]) - np.ones_like(a) / a.shape[0]; return p @ a @ p


def _svg_heatmap(path: Path, matrix: np.ndarray, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); cell, left, top = 110, 155, 72
    vals = [float(v) for v in matrix.ravel()]; scale = max(abs(v) for v in vals) or 1.0
    def color(v: float) -> str:
        z = max(-1.0, min(1.0, v / scale)); r = int(245 - max(z, 0) * 160); b = int(245 - max(-z, 0) * 160); g = int(245 - abs(z) * 110); return f"rgb({r},{g},{b})"
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="620"><style>text{{font-family:Arial;fill:#222}} .t{{font-size:18px;font-weight:bold}} .s{{font-size:12px}}</style><text class="t" x="12" y="28">{title}</text>']
    for j, name in enumerate(FAMILIES): parts.append(f'<text class="s" text-anchor="middle" x="{left+j*cell+44}" y="52">{name}</text>')
    for i, name in enumerate(FAMILIES):
        y = top + i * cell; parts.append(f'<text class="s" text-anchor="end" x="{left-8}" y="{y+48}">{name}</text>')
        for j in range(4):
            x = left + j * cell; value = float(matrix[i, j]); parts.append(f'<rect x="{x}" y="{y}" width="88" height="88" fill="{color(value)}"/><text class="s" text-anchor="middle" x="{x+44}" y="{y+50}">{value:+.3f}</text>')
    parts.append('</svg>'); path.write_text(''.join(parts), encoding='utf-8')


def analyze() -> dict[str, Any]:
    manifest = json.loads((REPORT_ROOT / "manifest.json").read_text(encoding="utf-8"))
    events = _load_events(DATA_ROOT / "events.jsonl"); terminal = _terminal_events(manifest, events)
    if len(terminal) < manifest["logical_calls"]: raise RuntimeError(f"cannot analyze incomplete run: {len(terminal)}/{manifest['logical_calls']}")
    response_rows: list[dict[str, Any]] = []; baseline: dict[tuple[str, int, str, str], dict[str, Any]] = {}; transfer: list[dict[str, Any]] = []
    for task in manifest["tasks"]:
        logical_id = stable_hash({"protocol": PROTOCOL, "tasks_hash": manifest["tasks_hash"], "task": task}); event = terminal[logical_id]; decisions = event.get("decisions"); expected = task["probe"]["y"]
        row = {"geometry": task["geometry"], "seed": task["seed"], "source": task["source"] or "", "target": task["target"], "condition": task["condition"], "probe_id": task["probe"]["case_id"], "template_id": task["probe"]["template_id"], "expected": json.dumps(expected), "decisions": json.dumps(decisions) if decisions is not None else "", "correct": int(decisions == expected) if decisions is not None else 0, "error_category": event.get("error_category") or "", "attempt": event.get("attempt", 0), "latency_s": event.get("latency_s"), "cost_usd": event.get("attempt_cost_usd"), "model": (event.get("provider_metadata") or {}).get("model", ""), "fingerprint": (event.get("provider_metadata") or {}).get("system_fingerprint", "")}
        response_rows.append(row)
        if task["condition"] == "baseline": baseline[(task["geometry"], task["seed"], task["target"], task["probe"]["case_id"])] = {"correct": row["correct"], "decisions": decisions, "expected": expected}
        else: transfer.append({"task": task, "event": event, "decisions": decisions, "correct": row["correct"]})
    write_csv(REPORT_ROOT / "response_level.csv", response_rows)
    seed_matrix_rows: list[dict[str, Any]] = []; aggregate_rows: list[dict[str, Any]] = []; component_rows: list[dict[str, Any]] = []; anchoring_rows: list[dict[str, Any]] = []
    lstar = _load_lstar(); matrices_ds: dict[tuple[str, int], np.ndarray] = {}; matrices_l: dict[str, np.ndarray] = {}
    for geometry in GEOMETRIES:
        for seed in SEEDS:
            rows_seed: list[dict[str, Any]] = []
            for source in FAMILIES:
                for target in FAMILIES:
                    vals = [item for item in transfer if item["task"]["geometry"] == geometry and item["task"]["seed"] == seed and item["task"]["source"] == source and item["task"]["target"] == target]
                    base = [baseline[(geometry, seed, target, item["task"]["probe"]["case_id"])] for item in vals]
                    bacc = statistics.mean(item["correct"] for item in base); tacc = statistics.mean(item["correct"] for item in vals); gain = tacc - bacc
                    row = {"geometry": geometry, "seed": seed, "source": source, "target": target, "baseline_accuracy": bacc, "transfer_accuracy": tacc, "L_DS": gain, "L_star": lstar[(geometry, source, target)]["L_star"], "J_obs": lstar[(geometry, source, target)]["J_obs"], "n": len(vals)}; rows_seed.append(row); seed_matrix_rows.append(row)
                    for j in range(3):
                        bcomp = statistics.mean(int(item["decisions"] is not None and item["decisions"][j] == item["expected"][j]) for item in base)
                        tcomp = statistics.mean(int(item["decisions"] is not None and item["decisions"][j] == item["expected"][j]) for item in vals)
                        component_rows.append({"geometry": geometry, "seed": seed, "source": source, "target": target, "component": j + 1, "baseline_accuracy": bcomp, "transfer_accuracy": tcomp, "L_DS": tcomp - bcomp})
                    for item in vals:
                        memory = item["task"]["memory"]; decisions = item["decisions"]; labels = [m["y"] for m in memory]
                        anchoring_rows.append({"geometry": geometry, "seed": seed, "source": source, "target": target, "probe_id": item["task"]["probe"]["case_id"], "correct": int(item["correct"]), "last_action_copy": int(bool(labels and decisions == labels[-1])) if decisions is not None else 0, "any_action_copy": int(any(decisions == label for label in labels)) if decisions is not None else 0, "component_last_copy": statistics.mean(int(decisions[j] == labels[-1][j]) for j in range(3)) if decisions is not None and labels else None})
            matrices_ds[(geometry, seed)] = _matrix(rows_seed, "L_DS")
    write_csv(REPORT_ROOT / "seed_level_transfer_matrices.csv", seed_matrix_rows)
    write_csv(REPORT_ROOT / "component_transfer.csv", component_rows)
    write_csv(REPORT_ROOT / "anchoring.csv", anchoring_rows)
    for geometry in GEOMETRIES:
        rows_g = [row for row in seed_matrix_rows if row["geometry"] == geometry]
        agg: list[dict[str, Any]] = []
        for source in FAMILIES:
            for target in FAMILIES:
                values = [float(row["L_DS"]) for row in rows_g if row["source"] == source and row["target"] == target]
                lvals = [float(row["L_star"]) for row in rows_g if row["source"] == source and row["target"] == target]
                agg.append({"geometry": geometry, "source": source, "target": target, "L_DS": statistics.mean(values), "L_star": statistics.mean(lvals), "seed_mean": statistics.mean(values), "seed_median": statistics.median(values), "seed_min": min(values), "seed_max": max(values), "seed_sd": statistics.stdev(values) if len(values)>1 else 0.0})
        matrices_l[geometry] = _matrix(agg, "L_DS"); aggregate_rows.extend(agg)
    write_csv(REPORT_ROOT / "aggregate_transfer_matrices.csv", aggregate_rows)
    seed_acc_rows = [{"geometry": row["geometry"], "seed": row["seed"], "source": row["source"], "target": row["target"], "baseline_accuracy": row["baseline_accuracy"], "transfer_accuracy": row["transfer_accuracy"], "L_DS": row["L_DS"]} for row in seed_matrix_rows]
    write_csv(REPORT_ROOT / "seed_level_accuracy.csv", seed_acc_rows)
    alignment: list[dict[str, Any]] = []; zero_rows: list[dict[str, Any]] = []; missed_rows: list[dict[str, Any]] = []; projections: list[dict[str, Any]] = []; residual_rows: list[dict[str, Any]] = []
    for geometry in GEOMETRIES:
        ds = matrices_l[geometry]; ls = _matrix([row for row in aggregate_rows if row["geometry"] == geometry], "L_star"); residual = ds - (float(np.sum(ds * ls)) / float(np.sum(ls * ls)) if np.sum(ls*ls) else 0.0) * ls; alpha = float(np.sum(ds * ls) / np.sum(ls * ls)) if np.sum(ls * ls) else 0.0
        alignment.append({"geometry": geometry, "raw_cosine": _cosine(ds, ls), "centered_cosine": _cosine(_centered(ds), _centered(ls)), "alpha": alpha})
        projections.append({"geometry": geometry, "alpha": alpha, "ds_frobenius": float(np.linalg.norm(ds)), "lstar_frobenius": float(np.linalg.norm(ls)), "residual_frobenius": float(np.linalg.norm(residual))})
        for i, source in enumerate(FAMILIES):
            for j, target in enumerate(FAMILIES):
                row = {"geometry": geometry, "source": source, "target": target, "L_DS": float(ds[i,j]), "L_star": float(ls[i,j]), "residual": float(residual[i,j])}; residual_rows.append(row)
                if float(ls[i,j]) == 0.0: zero_rows.append({**row, "zero_J_cell": int(source != target) if geometry == "DIAGONAL" else int((geometry == "BLOCK" and ((source in ("ACCESS","RELEASE")) != (target in ("ACCESS","RELEASE")))))})
                missed_rows.append({**row, "missed_transfer": float(ls[i,j] - ds[i,j])})
    write_csv(REPORT_ROOT / "geometry_alignment.csv", alignment); write_csv(REPORT_ROOT / "learner_projection.csv", projections); write_csv(REPORT_ROOT / "residual_transfer.csv", residual_rows); write_csv(REPORT_ROOT / "zero_information_transfer.csv", zero_rows); write_csv(REPORT_ROOT / "missed_transfer.csv", missed_rows)
    for geometry in GEOMETRIES: _svg_heatmap(REPORT_ROOT / "figures" / f"L_DS_{geometry.lower()}.svg", matrices_l[geometry], f"L DeepSeek {geometry}")
    health = {"protocol": PROTOCOL, "logical_expected": manifest["logical_calls"], "logical_terminal": len(terminal), "physical_attempts": len(events), "technical_retries": sum(int(e.get("attempt", 0)) for e in events), "semantic_ood": sum(e.get("error_category") == "out_of_domain" for e in events), "error_categories": dict(__import__("collections").Counter(e.get("error_category") for e in events if e.get("error_category"))), "coverage": len(terminal) / manifest["logical_calls"], "usage_coverage": sum(bool(e.get("token_usage")) for e in events) / len(events) if events else 0.0, "observed_cost_usd": sum(float(e.get("attempt_cost_usd") or 0) for e in events), "latency_mean_s": statistics.mean(float(e.get("latency_s") or 0) for e in events), "latency_median_s": statistics.median(float(e.get("latency_s") or 0) for e in events), "models": sorted({(e.get("provider_metadata") or {}).get("model") for e in events}), "fingerprints": sorted({(e.get("provider_metadata") or {}).get("system_fingerprint") for e in events})}
    atomic_json(REPORT_ROOT / "technical_health.json", health); atomic_json(REPORT_ROOT / "cost.json", {"observed_cost_usd": health["observed_cost_usd"], "hard_cap_usd": HARD_CAP_USD, "remaining_usd": HARD_CAP_USD - health["observed_cost_usd"]})
    return {"health": health, "alignment": alignment, "aggregate": aggregate_rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=PROTOCOL)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--forecast", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--confirm-real", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    args = parser.parse_args()
    if args.freeze:
        manifest = freeze_manifest(); print(json.dumps({"manifest": str(REPORT_ROOT / 'manifest.json'), "tasks_hash": manifest["tasks_hash"], "call_breakdown": manifest["call_breakdown"], "cost_forecast": manifest["cost_forecast"]}, indent=2))
    elif args.forecast:
        tasks = build_tasks(); print(json.dumps(cost_forecast(tasks), indent=2))
    elif args.run:
        print(json.dumps(asyncio.run(run_real(confirm_real=args.confirm_real)), indent=2))
    elif args.analyze:
        print(json.dumps(analyze(), indent=2, default=float))
    else:
        parser.error("choose --freeze, --forecast, --run, or --analyze")


if __name__ == "__main__":
    main()
