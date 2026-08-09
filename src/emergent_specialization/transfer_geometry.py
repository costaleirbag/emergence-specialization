"""TRANSFER-GEOMETRY-CONTROL-V1: frozen OPE geometry calibration.

This is a single-agent diagnostic.  It has no router, no society state, and no
adaptive selection.  All task streams are frozen before the Direct backend is
constructed.  The module also materializes the preregistered operator and toy
dynamics analyses from raw events.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import fcntl
import json
import math
import os
import random
import statistics
import subprocess
import tempfile
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from .credentials import CredentialStore
from .ecology_transfer import _append_event, _atomic_json, _logical_observation, _mean, _sample_sd
from .models import BackendResponse
from .providers import DeepSeekDirectBackend
from .semantic_ecology import GEOMETRY_ECOLOGIES, OPEGeometryV2Ecology, Case, stable_hash
from .transfer_operator import (analytical_jacobian, block_modes, block_matrix,
                                 centered_transfer, finite_difference_jacobian,
                                 geometry_metrics, rayleigh, toy_rhs)

ROOT = Path(__file__).resolve().parents[2]
REPORT_ROOT = ROOT / "reports/task-ecology/transfer-geometry-v1"
DATA_ROOT = ROOT / "data/auto-research/transfer-geometry-v1"
MANIFEST_ROOT = REPORT_ROOT / "manifests"
MODEL = "deepseek-v4-flash"
GEOMETRIES = ("GLOBAL", "BLOCK", "DIAGONAL")
SEEDS = (8101, 8102, 8103, 8104, 8105)
REPLICATES = 2
PROBE_COUNT = 8
HORIZONS = (4, 8)
HARD_CAP_USD = 1.50
RESERVATION_USD = 0.005
INPUT_PRICE = 0.14
CACHED_INPUT_PRICE = 0.0028
OUTPUT_PRICE = 0.28
PROTOCOL = "TRANSFER-GEOMETRY-CONTROL-V1"


def now() -> str:
    return datetime.now(UTC).isoformat()


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def _cost(response: BackendResponse) -> float | None:
    from .costs import estimate_usage_cost
    if response.observed_cost_usd is not None:
        value = float(response.observed_cost_usd)
        return value if math.isfinite(value) and value >= 0 else None
    return estimate_usage_cost(response.token_usage, input_per_million_tokens=INPUT_PRICE,
                               cached_input_per_million_tokens=CACHED_INPUT_PRICE,
                               output_per_million_tokens=OUTPUT_PRICE)


def _budget_path() -> Path:
    return REPORT_ROOT / "campaign_budget.json"


def _load_budget() -> dict[str, Any]:
    path = _budget_path()
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    value = {"protocol": PROTOCOL, "hard_cap_usd": HARD_CAP_USD, "spent_usd": 0.0,
             "reserved_usd": 0.0, "created_at_utc": now(), "history": []}
    _atomic_json(path, value)
    return value


def _budget_change(*, reserve: float = 0.0, release: float = 0.0, actual: float = 0.0) -> None:
    path = _budget_path(); lock_path = path.with_suffix(".lock")
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        budget = _load_budget()
        spent = float(budget.get("spent_usd", 0.0)); held = float(budget.get("reserved_usd", 0.0))
        cap = float(budget["hard_cap_usd"])
        if held + 1e-12 < release or spent + held - release + reserve + actual > cap + 1e-12:
            raise RuntimeError("transfer-geometry hard budget guard")
        budget["reserved_usd"] = held - release + reserve
        budget["spent_usd"] = spent + actual
        budget["updated_at_utc"] = now()
        _atomic_json(path, budget)


def _factor_rows(environment: Any) -> list[dict[str, Any]]:
    values = environment.metadata["factor_values"]
    return [{"factor_id": factor, "value": value} for factor, value in sorted(values.items())]


def _natural_cases(ecology: OPEGeometryV2Ecology, environment: Any, family: str, *, h: int) -> list[Case]:
    pool = ecology.case_pool(environment, family, template="train")
    rng = random.Random(0xA71CE + environment.seed * 104729 + sum(ord(x) for x in family) * 31)
    rng.shuffle(pool)
    return pool[:h]


def _teaching_cases(ecology: OPEGeometryV2Ecology, environment: Any, family: str, *, h: int) -> list[Case]:
    return ecology.training_cases(environment, family, h)


def _memory(ecology: OPEGeometryV2Ecology, cases: list[Case]) -> list[str]:
    return [ecology.render_experience(case) for case in cases]


def _task(*, geometry: str, seed: int, target: str, source: str | None, h: int,
          exposure_policy: str, case: Case, memory: list[str], memory_seed: int | None = None,
          replicate: int) -> dict[str, Any]:
    return {"geometry": geometry, "seed": seed, "target": target, "source": source,
            "h": h, "exposure_policy": exposure_policy, "replicate": replicate,
            "memory_environment_seed": memory_seed, "case": case.symbolic(), "memory": memory}


def build_tasks(geometry: str, seeds: tuple[int, ...] = SEEDS) -> list[dict[str, Any]]:
    ecology = GEOMETRY_ECOLOGIES[geometry]
    tasks: list[dict[str, Any]] = []
    for seed in seeds:
        environment = ecology.generate_environment(seed)
        foreign_seed = seeds[(seeds.index(seed) + 1) % len(seeds)]
        foreign_environment = ecology.generate_environment(foreign_seed)
        for target in ecology.families:
            probes = ecology.probe_cases(environment, target)
            for case in probes:
                for replicate in range(REPLICATES):
                    tasks.append(_task(geometry=geometry, seed=seed, target=target, source=None, h=0,
                                       exposure_policy="baseline", case=case, memory=[], replicate=replicate))
            for source in ecology.families:
                natural = _natural_cases(ecology, environment, source, h=8)
                teaching = _teaching_cases(ecology, environment, source, h=8)
                for policy, memories in (("natural", natural), ("teaching", teaching)):
                    for case in probes:
                        for replicate in range(REPLICATES):
                            tasks.append(_task(geometry=geometry, seed=seed, target=target, source=source, h=8,
                                               exposure_policy=policy, case=case, memory=_memory(ecology, memories), replicate=replicate))
            for policy, cases in (("natural", _natural_cases(ecology, environment, target, h=4)),
                                  ("teaching", _teaching_cases(ecology, environment, target, h=4))):
                for case in probes:
                    for replicate in range(REPLICATES):
                        tasks.append(_task(geometry=geometry, seed=seed, target=target, source=target, h=4,
                                           exposure_policy=policy, case=case, memory=_memory(ecology, cases), replicate=replicate))
            foreign_cases = _natural_cases(ecology, foreign_environment, target, h=8)
            for case in probes:
                for replicate in range(REPLICATES):
                    tasks.append(_task(geometry=geometry, seed=seed, target=target, source=target, h=8,
                                       exposure_policy="foreign_theta", case=case, memory=_memory(ecology, foreign_cases),
                                       memory_seed=foreign_seed, replicate=replicate))
    return tasks


def expected_calls() -> dict[str, int]:
    per_geometry = len(SEEDS) * (4 * 8 * 2 + 4 * 4 * 8 * 2 + 4 * 4 * 8 * 2 + 4 * 8 * 2 + 4 * 8 * 2 + 4 * 8 * 2)
    return {"baseline": 960, "natural_h8": 3840, "teaching_h8": 3840,
            "natural_h4_diagonal": 960, "teaching_h4_diagonal": 960,
            "foreign_theta_h8_diagonal": 960, "per_geometry": per_geometry,
            "total": per_geometry * len(GEOMETRIES)}


def _probe_balance(ecology: OPEGeometryV2Ecology, environment: Any, family: str) -> dict[str, int]:
    probes = ecology.probe_cases(environment, family)
    return {label: sum(case.expected == label for case in probes) for label in ecology.output_classes}


def _audit_one(geometry: str, seed: int, family: str) -> dict[str, Any]:
    ecology = GEOMETRY_ECOLOGIES[geometry]; env = ecology.generate_environment(seed)
    env2 = ecology.generate_environment(seed); probes = ecology.probe_cases(env, family)
    train = ecology.training_cases(env, family, 8); natural = _natural_cases(ecology, env, family, h=8)
    teaching = _teaching_cases(ecology, env, family, h=8)
    # The 100-seed audit uses an adjacent synthetic pair; the paid manifest
    # uses its fixed cyclic mapping over SEEDS.
    foreign_seed = seed + 1; foreign = _natural_cases(ecology, ecology.generate_environment(foreign_seed), family, h=8)
    rendered = "\n".join(ecology.render_case(family, case) for case in probes + train + natural + teaching + foreign)
    probe_ids = {case.case_id for case in probes}; stream_ids = {case.case_id for case in train + natural + teaching}
    balance = _probe_balance(ecology, env, family)
    expected = env.metadata["factor_ids_by_family"][family]
    factors = env.metadata["factor_values"]
    factor_shape = len(expected) == 3 and len(set(expected)) == 3
    no_leak = not any(token.lower() in rendered.lower() for token in ("theta", "factor", "threshold", "compatibility", "exception"))
    return {"geometry": geometry, "seed": seed, "family": family, "oracle_pass": all(ecology.solve(env, family, p.fields) == p.expected for p in probes),
            "deterministic_pass": env == env2, "balance_pass": all(v == 2 for v in balance.values()), "balance": balance,
            "probe_count": len(probes), "train_probe_disjoint": not (probe_ids & {c.case_id for c in train}),
            "natural_probe_disjoint": not (probe_ids & {c.case_id for c in natural}),
            "teaching_probe_disjoint": not (probe_ids & {c.case_id for c in teaching}), "natural_count": len(natural),
            "teaching_count": len(teaching), "nested_h4": [c.case_id for c in _natural_cases(ecology, env, family, h=4)] == [c.case_id for c in natural[:4]],
            "foreign_seed": foreign_seed, "foreign_semantic_family": all(c.family == family for c in foreign),
            "foreign_theta_differs": ecology.generate_environment(foreign_seed).metadata["factor_values"] != factors,
            "factor_shape_pass": factor_shape, "theta_leakage": not no_leak,
            "factor_ids": expected, "factor_count": len(env.metadata["factor_order"]),
            "predictive_identifiability_h4": __import__("emergent_specialization.semantic_ecology", fromlist=["predictive_identifiability"]).predictive_identifiability(ecology, env, family, 4)["predictively_identifiable"],
            "predictive_identifiability_h8": __import__("emergent_specialization.semantic_ecology", fromlist=["predictive_identifiability"]).predictive_identifiability(ecology, env, family, 8)["predictively_identifiable"]}


def offline_audit() -> list[dict[str, Any]]:
    seeds = tuple(range(100))
    rows = [_audit_one(geometry, seed, family) for geometry in GEOMETRIES for seed in seeds for family in GEOMETRY_ECOLOGIES[geometry].families]
    _write_csv(REPORT_ROOT / "generator_audit.csv", rows)
    for row in rows:
        required = (row["oracle_pass"], row["deterministic_pass"], row["balance_pass"], row["train_probe_disjoint"],
                    row["natural_probe_disjoint"], row["teaching_probe_disjoint"], row["nested_h4"], row["foreign_semantic_family"],
                    row["foreign_theta_differs"], row["factor_shape_pass"], not row["theta_leakage"])
        if not all(required):
            raise RuntimeError(f"offline geometry audit failed: {row}")
    # Exact designed matrices and a representative frozen-environment record.
    designed: list[dict[str, Any]] = []
    for geometry in GEOMETRIES:
        env = GEOMETRY_ECOLOGIES[geometry].generate_environment(SEEDS[0])
        for source_i, source in enumerate(GEOMETRY_ECOLOGIES[geometry].families):
            for target_i, target in enumerate(GEOMETRY_ECOLOGIES[geometry].families):
                designed.append({"geometry": geometry, "seed": SEEDS[0], "source": source, "target": target,
                                 "overlap": env.metadata["designed_overlap"][source_i][target_i]})
    _write_csv(REPORT_ROOT / "designed_geometry.csv", designed)
    return rows


def freeze_manifest(geometry: str) -> dict[str, Any]:
    tasks = build_tasks(geometry)
    expected = expected_calls()["per_geometry"]
    if len(tasks) != expected:
        raise RuntimeError(f"geometry task count mismatch {len(tasks)} != {expected}")
    ecology = GEOMETRY_ECOLOGIES[geometry]
    try:
        git_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        git_head = "unknown"
    manifest = {"protocol": PROTOCOL, "geometry": geometry, "git_head": git_head, "seeds": list(SEEDS), "families": list(ecology.families),
                "model": MODEL, "backend": "deepseek_direct", "thinking": "off", "replicates": REPLICATES,
                "probe_count": PROBE_COUNT, "tasks_hash": stable_hash(tasks), "logical_calls": len(tasks),
                "created_at_utc": now(), "tasks": tasks,
                "designed_geometry": ecology.generate_environment(SEEDS[0]).metadata["designed_overlap"],
                "factor_metadata": {str(seed): ecology.generate_environment(seed).metadata for seed in SEEDS}}
    MANIFEST_ROOT.mkdir(parents=True, exist_ok=True)
    _atomic_json(MANIFEST_ROOT / f"{geometry.lower()}.json", manifest)
    return manifest


def freeze_all_manifests() -> list[dict[str, Any]]:
    return [freeze_manifest(geometry) for geometry in GEOMETRIES]


def _prompt(ecology: OPEGeometryV2Ecology, task: dict[str, Any]) -> str:
    data = task["case"]
    case = Case(data["family"], data["case_id"], data["template"], tuple(data["entities"]), data["fields"], data["expected"])
    return ecology.render_query(case, task["memory"])


async def _run_one(geometry: str, *, confirm_real: bool) -> dict[str, Any]:
    if not confirm_real:
        raise SystemExit("real transfer-geometry execution requires --confirm-real")
    manifest_path = MANIFEST_ROOT / f"{geometry.lower()}.json"
    if not manifest_path.exists():
        raise RuntimeError("frozen geometry manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["logical_calls"] != expected_calls()["per_geometry"]:
        raise RuntimeError("manifest logical count mismatch")
    output = DATA_ROOT / geometry.lower(); output.mkdir(parents=True, exist_ok=True)
    events_path = output / "events.jsonl"; status_path = output / "manifest.json"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()] if events_path.exists() else []
    if status_path.exists():
        status = json.loads(status_path.read_text(encoding="utf-8"))
        if status.get("tasks_hash") != manifest["tasks_hash"]:
            raise RuntimeError("existing geometry output does not match frozen manifest")
        if status.get("status") == "completed":
            return status
        status["status"] = "resuming"; status["resumed_at_utc"] = now()
    else:
        status = {"protocol": PROTOCOL, "geometry": geometry, "status": "initialized", "tasks_hash": manifest["tasks_hash"],
                  "logical_calls": manifest["logical_calls"], "created_at_utc": now()}
    _atomic_json(status_path, status)
    terminal = {event.get("logical_id") for event in events if event.get("error") is None or event.get("error_category") == "out_of_domain"}
    attempts: dict[str, int] = defaultdict(int)
    for event in events:
        attempts[event.get("logical_id")] = max(attempts[event.get("logical_id")], int(event.get("attempt", 0)) + 1)
    cost_total = sum(float(event.get("attempt_cost_usd") or 0.0) for event in events)
    physical = len(events); retries = sum(1 for event in events if int(event.get("attempt", 0)) > 0)
    backend = None
    try:
        key = CredentialStore().get(source="keychain")
        backend = DeepSeekDirectBackend(api_key=key, thinking="off", max_tokens=256)
        ecology = GEOMETRY_ECOLOGIES[geometry]
        for task in manifest["tasks"]:
            logical_id = stable_hash({"geometry": geometry, "task": task, "tasks_hash": manifest["tasks_hash"]})
            if logical_id in terminal:
                continue
            start = attempts.get(logical_id, 0)
            if start >= 2:
                raise RuntimeError(f"retry exhaustion for {logical_id}")
            for attempt in range(start, 2):
                _budget_change(reserve=RESERVATION_USD)
                try:
                    response = await backend.complete(system_prompt="You are a single-agent procedural transfer diagnostic. Use resolved cases only as feedback memory.",
                                                      user_prompt=_prompt(ecology, task), model=MODEL,
                                                      model_parameters={"thinking": "off", "max_tokens": 256})
                except Exception:
                    _budget_change(release=RESERVATION_USD)
                    raise
                physical += 1; value = _cost(response)
                if value is None:
                    _budget_change(release=RESERVATION_USD)
                    raise RuntimeError("cost accounting unavailable; stopped before accepting response")
                _budget_change(release=RESERVATION_USD, actual=float(value)); cost_total += float(value)
                raw = response.raw_response
                answer = confidence = error = None
                if raw:
                    try:
                        decoded = json.loads(raw)
                        answer = decoded.get("answer") if isinstance(decoded, dict) else None
                        confidence = float(decoded.get("confidence")) if isinstance(decoded, dict) else None
                        if not isinstance(answer, str) or answer not in ecology.output_classes or confidence is None or not 0 <= confidence <= 1:
                            error = "out_of_domain" if answer not in ecology.output_classes else "schema"
                    except (ValueError, TypeError, json.JSONDecodeError):
                        error = "parse_error"
                else:
                    error = response.error_category or response.error or "empty_content"
                provider = response.provider_metadata or {}
                if provider.get("model") != MODEL:
                    error = "invalid_model"
                if response.error:
                    error = response.error
                case = task["case"]
                event = {"logical_id": logical_id, "geometry": geometry, "attempt": attempt, "task": task,
                         "answer": answer, "confidence": confidence, "correct": answer == case["expected"], "error": error,
                         "error_category": response.error_category or error, "raw_model_response": raw,
                         "latency_s": response.latency_s, "token_usage": response.token_usage,
                         "provider_metadata": provider, "attempt_cost_usd": float(value), "finished_at_utc": now()}
                _append_event(events_path, event); events.append(event)
                if error is None or error == "out_of_domain":
                    terminal.add(logical_id); break
                retry_category = response.error_category or error
                if not response.retryable or retry_category not in {"parse_error", "empty_content", "transient_transport", "transport", "429", "rate_limit", "http_429"}:
                    raise RuntimeError(error)
                retries += 1
            else:
                raise RuntimeError("retry exhaustion")
        status.update(status="completed", physical_attempts=physical, retries=retries, observed_cost_usd=cost_total,
                      finished_at_utc=now())
    except Exception as exc:
        status.update(status="failed", failure=f"{type(exc).__name__}: {exc}", physical_attempts=physical,
                      retries=retries, observed_cost_usd=cost_total, finished_at_utc=now())
    finally:
        if backend is not None:
            await backend.close()
        _atomic_json(status_path, status)
    return status


def _rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values); i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]: j += 1
        rank = (i + j) / 2 + 1
        for index in range(i, j + 1): ranks[order[index]] = rank
        i = j + 1
    return ranks


def _spearman(a: list[float], b: list[float]) -> float | None:
    if len(a) != len(b) or len(a) < 2: return None
    ra, rb = _rank(a), _rank(b)
    ma, mb = statistics.mean(ra), statistics.mean(rb)
    da = [x - ma for x in ra]; db = [x - mb for x in rb]
    den = math.sqrt(sum(x*x for x in da) * sum(x*x for x in db))
    return sum(x*y for x, y in zip(da, db)) / den if den else 0.0


def _cosine_centered(a: np.ndarray, b: np.ndarray) -> float:
    P = np.eye(a.shape[0]) - np.ones_like(a) / a.shape[0]
    x = P @ a @ P; y = P @ b @ P
    den = float(np.linalg.norm(x) * np.linalg.norm(y))
    return float(np.sum(x * y) / den) if den else 0.0


def _svg_heatmap(path: Path, matrix: np.ndarray, title: str, labels: tuple[str, ...]) -> None:
    size, left, top, cell = 620, 150, 70, 100
    def color(v: float) -> str:
        z = max(-1.0, min(1.0, v)); r = int(245 - max(z, 0) * 160); b = int(245 - max(-z, 0) * 160); g = int(245 - abs(z) * 110)
        return f"rgb({r},{g},{b})"
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}"><style>text{{font-family:Arial;fill:#222}} .t{{font-size:18px;font-weight:bold}} .s{{font-size:12px}}</style>', f'<text class="t" x="12" y="28">{title}</text>']
    for j, label in enumerate(labels): parts.append(f'<text class="s" text-anchor="middle" x="{left+j*cell+45}" y="52">{label}</text>')
    for i, label in enumerate(labels):
        y = top + i * cell; parts.append(f'<text class="s" text-anchor="end" x="{left-8}" y="{y+48}">{label}</text>')
        for j in range(len(labels)):
            x = left + j * cell; v = float(matrix[i, j]); parts.append(f'<rect x="{x}" y="{y}" width="88" height="88" fill="{color(v)}"/>')
            parts.append(f'<text class="s" text-anchor="middle" x="{x+44}" y="{y+50}">{v:+.3f}</text>')
    parts.append('</svg>'); path.write_text(''.join(parts), encoding='utf-8')


def _aggregate_geometry(geometry: str) -> dict[str, Any]:
    ecology = GEOMETRY_ECOLOGIES[geometry]; data_dir = DATA_ROOT / geometry.lower(); events_path = data_dir / "events.jsonl"
    if not events_path.exists(): raise FileNotFoundError(events_path)
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    out_dir = REPORT_ROOT / geometry.lower(); figure_dir = out_dir / "figures"; figure_dir.mkdir(parents=True, exist_ok=True)
    grouped: dict[tuple[int, str, str | None, int, str], list[dict[str, Any]]] = defaultdict(list)
    response_rows: list[dict[str, Any]] = []
    for event in events:
        task = event["task"]; key = (task["seed"], task["target"], task["source"], task["h"], task["exposure_policy"]); grouped[key].append(event)
        response_rows.append({"geometry": geometry, "seed": task["seed"], "source": task["source"] or "none", "target": task["target"], "h": task["h"],
                              "exposure_policy": task["exposure_policy"], "replicate": task["replicate"], "case_id": task["case"]["case_id"],
                              "answer": event.get("answer"), "expected": task["case"]["expected"], "correct": event.get("correct"),
                              "confidence": event.get("confidence"), "latency_s": event.get("latency_s"), "error": event.get("error"),
                              "input_tokens": (event.get("token_usage") or {}).get("prompt_tokens"), "output_tokens": (event.get("token_usage") or {}).get("completion_tokens"),
                              "cost_usd": event.get("attempt_cost_usd"), "memory_count": len(task.get("memory") or [])})
    _write_csv(out_dir / "response_level.csv", response_rows)
    rows: list[dict[str, Any]] = []
    # ``source`` is ``None`` for baseline rows and a string for exposed rows;
    # normalize it for deterministic ordering instead of comparing None/str.
    grouped_items = sorted(grouped.items(), key=lambda item: (
        item[0][0], item[0][1], item[0][2] or "", item[0][3], item[0][4]))
    for (seed, target, source, h, policy), vals in grouped_items:
        valid = [v for v in vals if _logical_observation(v)]
        rows.append({"geometry": geometry, "seed": seed, "source": source or "none", "target": target, "h": h,
                     "exposure_policy": policy, "n": len(valid), "accuracy": _mean([float(v.get("correct", False)) for v in valid]),
                     "errors": len(vals)-len(valid), "mean_confidence": _mean([float(v["confidence"]) for v in valid if v.get("confidence") is not None])})
    _write_csv(out_dir / "checkpoint_rows.csv", rows)
    lookup = {(r["geometry"], r["seed"], r["target"]): r["accuracy"] for r in rows if r["source"] == "none" and r["h"] == 0 and r["exposure_policy"] == "baseline"}
    matrix_rows: list[dict[str, Any]] = []; L_rows: list[dict[str, Any]]; L_rows = []
    for policy in ("natural", "teaching"):
        for seed in SEEDS:
            matrix = np.zeros((4, 4), dtype=float)
            for i, source in enumerate(ecology.families):
                for j, target in enumerate(ecology.families):
                    value = next((r["accuracy"] - lookup[(geometry, seed, target)] for r in rows if r["seed"] == seed and r["source"] == source and r["target"] == target and r["h"] == 8 and r["exposure_policy"] == policy), None)
                    matrix[i, j] = float(value or 0.0)
                    L_rows.append({"geometry": geometry, "seed": seed, "exposure_policy": policy, "source": source, "target": target, "L": value})
            for i, source in enumerate(ecology.families):
                for j, target in enumerate(ecology.families): matrix_rows.append({"geometry": geometry, "seed": seed, "exposure_policy": policy, "source": source, "target": target, "L": matrix[i,j]})
    _write_csv(out_dir / "environment_level_L.csv", L_rows)
    aggregate_rows: list[dict[str, Any]] = []; spectral_rows: list[dict[str, Any]] = []; metrics_rows: list[dict[str, Any]] = []
    env_mean: dict[str, np.ndarray] = {}
    for policy in ("natural", "teaching"):
        mats = []
        for seed in SEEDS:
            mat = np.array([[next(r["L"] for r in L_rows if r["seed"] == seed and r["exposure_policy"] == policy and r["source"] == s and r["target"] == t) for t in ecology.families] for s in ecology.families], dtype=float)
            mats.append(mat)
            m = geometry_metrics(mat); T = centered_transfer(mat)
            blocks = [0,0,1,1]; within = [mat[i,j] for i in range(4) for j in range(4) if i != j and blocks[i] == blocks[j]]; cross = [mat[i,j] for i in range(4) for j in range(4) if blocks[i] != blocks[j]]
            metrics_rows.append({"geometry": geometry, "seed": seed, "exposure_policy": policy, **m, "B": float(np.mean(within)-np.mean(cross)),
                                 "lambda_block": rayleigh(T, [1,1,-1,-1]), "lambda_AB": rayleigh(T, [1,-1,0,0]), "lambda_CD": rayleigh(T, [0,0,1,-1])})
            for i, source in enumerate(ecology.families):
                for j, target in enumerate(ecology.families): aggregate_rows.append({"geometry": geometry, "seed": seed, "exposure_policy": policy, "source": source, "target": target, "L": mat[i,j]})
        env_mean[policy] = np.mean(mats, axis=0)
        _svg_heatmap(figure_dir / f"{geometry.lower()}_L_{policy}.svg", env_mean[policy], f"{geometry} L {policy}", ecology.families)
    _write_csv(out_dir / "aggregate_L.csv", aggregate_rows); _write_csv(out_dir / "geometry_metrics.csv", metrics_rows)
    for policy, mat in env_mean.items():
        G = np.asarray(ecology.generate_environment(SEEDS[0]).metadata["designed_overlap"], dtype=float)
        off = ~np.eye(4, dtype=bool); spectral_rows.append({"geometry": geometry, "exposure_policy": policy, "spearman_offdiag_G_L": _spearman(G[off].tolist(), mat[off].tolist()),
                                                              "centered_frobenius_cosine": _cosine_centered(G, (mat+mat.T)/2), **geometry_metrics(mat)})
    _write_csv(out_dir / "spectral_metrics.csv", spectral_rows)
    # Natural-vs-teaching diagonal dose and foreign-theta specificity.
    gap_rows=[]; theta_rows=[]
    for seed in SEEDS:
        for family in ecology.families:
            base = lookup[(geometry, seed, family)]
            nat8 = next(r["accuracy"] for r in rows if r["seed"]==seed and r["target"]==family and r["source"]==family and r["h"]==8 and r["exposure_policy"]=="natural")
            teach8 = next(r["accuracy"] for r in rows if r["seed"]==seed and r["target"]==family and r["source"]==family and r["h"]==8 and r["exposure_policy"]=="teaching")
            nat4 = next(r["accuracy"] for r in rows if r["seed"]==seed and r["target"]==family and r["source"]==family and r["h"]==4 and r["exposure_policy"]=="natural")
            teach4 = next(r["accuracy"] for r in rows if r["seed"]==seed and r["target"]==family and r["source"]==family and r["h"]==4 and r["exposure_policy"]=="teaching")
            foreign = next(r["accuracy"] for r in rows if r["seed"]==seed and r["target"]==family and r["source"]==family and r["h"]==8 and r["exposure_policy"]=="foreign_theta")
            gap_rows.append({"geometry":geometry,"seed":seed,"family":family,"baseline":base,"natural_h4":nat4,"natural_h8":nat8,"teaching_h4":teach4,"teaching_h8":teach8,"gap_D_h8":teach8-nat8,"gap_Q_h8":None})
            theta_rows.append({"geometry":geometry,"seed":seed,"family":family,"same_theta_natural_h8":nat8,"foreign_theta_h8":foreign,"S_theta":nat8-foreign})
    _write_csv(out_dir / "exposure_gap.csv", gap_rows); _write_csv(out_dir / "theta_specificity.csv", theta_rows)
    return {"geometry": geometry, "events": len(events), "metrics": metrics_rows, "spectral": spectral_rows}


def validate_geometry_output(geometry: str) -> dict[str, Any]:
    """Offline technical health gate for one completed geometry."""
    manifest = json.loads((MANIFEST_ROOT / f"{geometry.lower()}.json").read_text(encoding="utf-8"))
    status = json.loads((DATA_ROOT / geometry.lower() / "manifest.json").read_text(encoding="utf-8"))
    events = [json.loads(line) for line in (DATA_ROOT / geometry.lower() / "events.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events: by_id[event["logical_id"]].append(event)
    terminal = {logical_id: [event for event in values if event.get("error") is None or event.get("error_category") == "out_of_domain"]
                for logical_id, values in by_id.items()}
    provider_models = {event.get("provider_metadata", {}).get("model") for event in events}
    # A recovered retry is identified by the failed predecessor, not by the
    # successful attempt (whose error field is necessarily empty).
    retry_categories = []
    for values in by_id.values():
        if len(values) > 1:
            retry_categories.extend(event.get("error_category") or event.get("error")
                                    for event in values if event.get("error") and event.get("error_category") != "out_of_domain")
    ood = sum(event.get("error_category") == "out_of_domain" for event in events)
    health = {"geometry": geometry, "status": status.get("status"), "expected_logical": manifest["logical_calls"],
              "unique_logical": len(by_id), "complete_logical": sum(bool(v) for v in terminal.values()),
              "physical_attempts": len(events), "technical_retries": sum(1 for event in events if int(event.get("attempt", 0)) > 0),
              "retry_categories": retry_categories, "semantic_ood": ood, "provider_models": sorted(str(x) for x in provider_models),
              "duplicate_terminal_logical": sum(len(v) > 1 for v in terminal.values()),
              "cost_from_events": sum(float(event.get("attempt_cost_usd") or 0.0) for event in events),
              "observed_cost": status.get("observed_cost_usd"),
              "clean_coverage": len(by_id) == manifest["logical_calls"] and all(bool(v) for v in terminal.values()),
              "model_identity_pass": provider_models <= {MODEL}}
    health["healthy"] = bool(health["status"] == "completed" and health["clean_coverage"] and health["model_identity_pass"] and health["duplicate_terminal_logical"] == 0)
    return health


def _toy_report() -> list[dict[str, Any]]:
    path = REPORT_ROOT / "aggregate_L.csv"
    if not path.exists(): return []
    with path.open(newline="", encoding="utf-8") as handle: rows = list(csv.DictReader(handle))
    out=[]
    for geometry in GEOMETRIES:
        vals = [r for r in rows if r["geometry"] == geometry and r["exposure_policy"] == "natural"]
        matrix = np.array([[statistics.mean(float(r["L"]) for r in vals if r["source"] == s and r["target"] == t) for t in GEOMETRY_ECOLOGIES[geometry].families] for s in GEOMETRY_ECOLOGIES[geometry].families])
        for kappa in (0.25, 0.5, 1.0, 2.0, 4.0):
            N=4; beta=1.0; gamma=1.0; eta=kappa*N*gamma/beta; a=np.zeros((N,4)); a[0,0]=1e-4; dt=0.1
            for _ in range(300): a += dt * toy_rhs(a,matrix,beta=beta,eta=eta,gamma=gamma)
            contrast = float(np.linalg.norm(a - a.mean(axis=0, keepdims=True)))
            out.append({"geometry":geometry,"kappa":kappa,"contrast_norm":contrast,"dominant_agent":int(np.argmax(np.linalg.norm(a,axis=1))),"label":"TOY DYNAMICS USING EMPIRICAL TRANSFER OPERATOR — NOT AN LLM SOCIETY RESULT"})
    _write_csv(REPORT_ROOT / "toy_dynamics.csv", out); return out


def aggregate_all() -> dict[str, Any]:
    results = [_aggregate_geometry(g) for g in GEOMETRIES]
    _toy_report()
    # Keep candidate-specific files immutable and also expose protocol-level
    # combined tables for downstream analysis.
    for filename in ("response_level.csv", "checkpoint_rows.csv", "environment_level_L.csv",
                     "aggregate_L.csv", "geometry_metrics.csv", "spectral_metrics.csv",
                     "exposure_gap.csv", "theta_specificity.csv"):
        merged: list[dict[str, Any]] = []
        for geometry in GEOMETRIES:
            path = REPORT_ROOT / geometry.lower() / filename
            if path.exists():
                with path.open(newline="", encoding="utf-8") as handle:
                    merged.extend(dict(row) for row in csv.DictReader(handle))
        if merged:
            _write_csv(REPORT_ROOT / filename, merged)
    return {"protocol": PROTOCOL, "geometries": results, "status": "aggregated"}


def plan() -> dict[str, Any]:
    calls = expected_calls(); recent = []
    for candidate in ("ope", "cwde"):
        path = ROOT / f"data/auto-research/ecology-transfer-qualification-v1/{candidate}/manifest.json"
        if path.exists():
            report = json.loads(path.read_text(encoding="utf-8")); recent.append((float(report.get("observed_cost_usd", 0.0) or 0.0), int(report.get("logical_calls", 1920))))
    observed_rates = [cost / logical for cost, logical in recent if logical > 0 and cost >= 0]
    # The qualification manifests are the nearest completed semantic runs;
    # use their observed per-logical-call rate, not old GF(7) prices.
    rate = statistics.mean(observed_rates) if observed_rates else 0.000025
    forecast = calls["total"] * rate
    result = {"protocol": PROTOCOL, "expected_calls": calls, "recent_rate_usd_per_call": rate,
              "forecast_nominal_usd": forecast, "forecast_with_25pct_retry_margin_usd": forecast*1.25,
              "hard_cap_usd": HARD_CAP_USD, "within_cap": forecast*1.25 <= HARD_CAP_USD, "seeds": list(SEEDS),
              "geometries": list(GEOMETRIES), "model": MODEL, "backend": "deepseek_direct"}
    _atomic_json(REPORT_ROOT / "plan.json", result); return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline-audit", action="store_true")
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--aggregate", action="store_true")
    parser.add_argument("--confirm-real", action="store_true")
    args = parser.parse_args()
    if args.offline_audit:
        rows = offline_audit(); print(json.dumps({"rows": len(rows), "status": "PASS"}, indent=2)); return
    if args.freeze:
        manifests = freeze_all_manifests(); print(json.dumps({"manifests": len(manifests), "calls": expected_calls()}, indent=2)); return
    if args.plan:
        print(json.dumps(plan(), indent=2)); return
    if args.run:
        if not args.confirm_real: raise SystemExit("--run requires --confirm-real")
        result = asyncio.run(_run_all(confirm_real=True)); print(json.dumps(result, indent=2)); return
    if args.aggregate:
        print(json.dumps(aggregate_all(), indent=2)); return
    parser.error("choose --offline-audit, --freeze, --plan, --run, or --aggregate")


async def _run_all(*, confirm_real: bool) -> dict[str, Any]:
    results=[]
    for geometry in GEOMETRIES:
        results.append(await _run_one(geometry, confirm_real=confirm_real))
    return {"protocol": PROTOCOL, "results": results, "budget": _load_budget()}


if __name__ == "__main__":
    main()
