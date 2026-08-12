"""Resumable Direct-DeepSeek executor for the frozen Theory V1 MACRO stage.

This is a protocol runner, not a replacement society implementation.  It
implements only the declared 16 social seeds, 18 cells, 128 online tasks and
four post-t0 probe checkpoints.  All routing randomness, sharing randomness,
task streams and evaluation supports are deterministic and frozen in the
manifest before the first MACRO call.
"""

from __future__ import annotations

import asyncio
import collections
import fcntl
import itertools
import json
import math
import os
import random
import statistics
import subprocess
import tempfile
from pathlib import Path
from datetime import UTC, datetime
from typing import Any, Sequence

from .. import observable_learner_calibration as learner
from ..credentials import CredentialStore
from ..models import BackendResponse
from ..providers import DeepSeekDirectBackend
from .ecologies import AffineBooleanV1, V31Fresh
from .micro_design import ECOLOGIES, MACRO_CHECKPOINTS, MACRO_ROUNDS, N_NICHES, PROBES_PER_NICHE, SOCIAL_SEEDS, macro_cells, stable_hash
from .micro_runner import HARD_CAP_USD, INPUT_PRICE, CACHED_INPUT_PRICE, OUTPUT_PRICE, MODEL, THINKING, MAX_TOKENS, REPORT_ROOT, DATA_ROOT, SYSTEM_PROMPT, OUTPUT_INSTRUCTION

MACRO_ROOT = DATA_ROOT / "macro"
MACRO_REPORT = REPORT_ROOT / "macro_execution_manifest.json"
PROTOCOL = "THEORY-V1"
NUM_AGENTS = 4
MEMORY_MIN = 1
CONCURRENCY = 32
MAX_ATTEMPTS = 2
RESERVATION_USD = 0.00050
RETRYABLE = {"parse_error", "empty_content", "transient_transport", "transport", "rate_limit", "server_error", "overloaded"}


def now() -> str:
    return datetime.now(UTC).isoformat()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True) + "\n"); handle.flush(); os.fsync(handle.fileno())


def _constructor(ecology: str) -> Any:
    return V31Fresh if ecology == "V31_FRESH" else AffineBooleanV1


def _support(ecology: str) -> list[tuple[int, ...]]:
    return list(itertools.product(range(4), repeat=3)) if ecology == "V31_FRESH" else list(itertools.product(range(2), repeat=6))


def _case(ecology: str, seed: int, niche: int, x: tuple[int, ...], role: str, index: int) -> dict[str, Any]:
    resolved = _constructor(ecology).resolved(seed, niche, x, role)
    return {"case_id": f"{ecology}:{seed}:{role}:{niche}:{index}:{''.join(map(str, x))}", "niche": niche, "x": list(x), "y": list(resolved.y), "template_id": int(resolved.template_id), "role": role}


def _render(ecology: str, item: dict[str, Any]) -> str:
    resolved = _constructor(ecology).resolved(int(item.get("seed", 0)), int(item["niche"]), tuple(item["x"]), item["role"])
    return _constructor(ecology).render(resolved)


def render_user(ecology: str, task: dict[str, Any], memory: Sequence[dict[str, Any]]) -> str:
    parts: list[str] = []
    if memory:
        parts.append("Prior resolved cases:\n" + "\n\n".join(f"{_render(ecology, item)}\nResolved decision: {json.dumps(item['y'], separators=(',', ':'))}" for item in memory))
    parts.append("CURRENT CASE:\n" + _render(ecology, task))
    parts.append(OUTPUT_INSTRUCTION)
    return "\n\n".join(parts)


def _balanced_values(ecology: str, seed: int, count: int) -> list[int]:
    values = [niche for niche in range(N_NICHES) for _ in range(count // N_NICHES)]
    random.Random(seed * 7919 + count * 31).shuffle(values)
    return values


def _seed_spec(ecology: str, seed: int) -> dict[str, Any]:
    support = _support(ecology); rng = random.Random(seed * 104729 + 701)
    evaluation = sorted(rng.sample(support, PROBES_PER_NICHE))
    remaining = [x for x in support if x not in set(evaluation)]
    task_rng = random.Random(seed * 1009 + 501)
    order = _balanced_values(ecology, seed, MACRO_ROUNDS)
    constructor = _constructor(ecology)
    online = []
    for t, niche in enumerate(order, 1):
        x = remaining[task_rng.randrange(len(remaining))]
        resolved = constructor.resolved(seed, niche, x, "online")
        online.append({"t": t, "niche": niche, "x": list(x), "y": list(resolved.y), "template_id": int(resolved.template_id), "role": "online"})
    routing_rng = random.Random(seed * 65537 + 991)
    routing_u = [routing_rng.random() for _ in range(MACRO_ROUNDS)]
    sharing_rng = random.Random(seed * 65537 + 1991)
    sharing_u = [[sharing_rng.random() for _ in range(NUM_AGENTS)] for _ in range(MACRO_ROUNDS)]
    return {"ecology": ecology, "seed": seed, "evaluation_x": [list(x) for x in evaluation], "online": online, "routing_u": routing_u, "sharing_u": sharing_u, "task_stream_hash": stable_hash(online), "evaluation_hash": stable_hash(evaluation)}


def expected_calls() -> dict[str, int]:
    t0 = sum(len(SOCIAL_SEEDS[e]) for e in ECOLOGIES) * NUM_AGENTS * N_NICHES * PROBES_PER_NICHE
    cells = sum(len(SOCIAL_SEEDS[e]) for e in ECOLOGIES) * len(macro_cells())
    post = cells * (len(MACRO_CHECKPOINTS) - 1) * NUM_AGENTS * N_NICHES * PROBES_PER_NICHE
    online = cells * MACRO_ROUNDS
    return {"t0": t0, "online": online, "post_checkpoints": post, "total": t0 + online + post, "per_cell": MACRO_ROUNDS + (len(MACRO_CHECKPOINTS) - 1) * NUM_AGENTS * N_NICHES * PROBES_PER_NICHE}


def build_manifest() -> dict[str, Any]:
    seeds = {(e, seed): _seed_spec(e, seed) for e in ECOLOGIES for seed in SOCIAL_SEEDS[e]}
    cells = [{"cell_id": i, **cell} for i, cell in enumerate(macro_cells())]
    counts = expected_calls()
    payload = {"protocol": PROTOCOL, "created_at_utc": now(), "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPORT_ROOT.parents[1], text=True).strip(), "model": MODEL, "provider": "DeepSeek Direct", "thinking": THINKING, "max_tokens": MAX_TOKENS, "hard_cap_usd": HARD_CAP_USD, "ecologies": list(ECOLOGIES), "social_seeds": {e: list(SOCIAL_SEEDS[e]) for e in ECOLOGIES}, "cells": cells, "seed_specs": {f"{e}:{s}": spec for (e, s), spec in seeds.items()}, "expected_calls": counts, "logical_calls": counts["total"], "task_order": "t0 then time-major ecology/seed/cell; checkpoint probes after each cell's 128 online tasks"}
    payload["manifest_hash"] = stable_hash(payload)
    if MACRO_REPORT.exists():
        old = json.loads(MACRO_REPORT.read_text(encoding="utf-8"))
        if old.get("manifest_hash") != payload["manifest_hash"]: raise RuntimeError("existing MACRO manifest differs")
        return old
    atomic_json(MACRO_REPORT, payload); return payload


def preflight() -> dict[str, Any]:
    """Reforecast MACRO from realized MICRO cost and rendered prompts."""
    micro_status_path = DATA_ROOT / "micro_status.json"
    if not micro_status_path.exists(): raise RuntimeError("MICRO status is missing")
    micro_status = json.loads(micro_status_path.read_text(encoding="utf-8"))
    if micro_status.get("status") != "completed": raise RuntimeError("MACRO preflight requires completed MICRO")
    manifest = build_manifest()
    micro_cost = float(micro_status.get("observed_cost_usd") or 0.0)
    micro_physical = int(micro_status.get("physical_attempts") or 0)
    if micro_physical <= 0: raise RuntimeError("MICRO has no billable attempts")
    micro_mean_cost = micro_cost / micro_physical
    micro_chars = 2656.732306985294
    macro_chars: list[int] = []
    for key, spec in manifest["seed_specs"].items():
        ecology = spec["ecology"]; seed = int(spec["seed"])
        for niche in range(N_NICHES):
            probe = _probe(ecology, seed, spec, niche, 0, 0)
            macro_chars.append(len(SYSTEM_PROMPT) + len(render_user(ecology, probe, [])))
        max_k = max(int(cell["k"]) for cell in manifest["cells"])
        max_memory = [_case(ecology, seed, i % N_NICHES, tuple(spec["online"][i % len(spec["online"])] ["x"]), "online", i) for i in range(max_k)]
        for item in spec["online"][:8]:
            macro_chars.append(len(SYSTEM_PROMPT) + len(render_user(ecology, item, max_memory)))
    ratio = statistics.mean(macro_chars) / micro_chars
    projected_macro = micro_mean_cost * manifest["logical_calls"] * ratio
    decision = micro_cost + 1.30 * projected_macro <= HARD_CAP_USD
    result = {"protocol": PROTOCOL, "micro_actual_cost_usd": micro_cost, "micro_physical_attempts": micro_physical, "micro_mean_cost_usd_per_attempt": micro_mean_cost, "macro_logical_calls": manifest["logical_calls"], "macro_prompt_chars_min": min(macro_chars), "macro_prompt_chars_max": max(macro_chars), "macro_prompt_chars_mean": statistics.mean(macro_chars), "prompt_ratio_to_micro": ratio, "projected_macro_cost_usd": projected_macro, "projected_total_cost_usd": micro_cost + projected_macro, "projected_total_with_30pct_remaining_margin_usd": micro_cost + 1.30 * projected_macro, "hard_ceiling_usd": HARD_CAP_USD, "decision": "PROCEED_TO_MACRO" if decision else "STOP_BEFORE_MACRO"}
    atomic_json(REPORT_ROOT / "macro_preflight.json", result)
    return result


def _budget_change(*, reserve: float = 0.0, release: float = 0.0, actual: float = 0.0) -> dict[str, Any]:
    path = DATA_ROOT / "campaign_budget.json"; lock_path = path.with_suffix(".lock"); path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        budget = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"protocol": PROTOCOL, "hard_cap_usd": HARD_CAP_USD, "spent_usd": 0.0, "reserved_usd": 0.0}
        spent, held = float(budget.get("spent_usd", 0.0)), float(budget.get("reserved_usd", 0.0))
        if held + 1e-12 < release or spent + held - release + reserve + actual > HARD_CAP_USD + 1e-12: raise RuntimeError("Theory V1 global hard budget guard")
        budget.update(spent_usd=spent + actual, reserved_usd=held - release + reserve, updated_at_utc=now()); atomic_json(path, budget); return budget


def _cost(response: BackendResponse) -> float | None:
    from ..costs import estimate_usage_cost
    return estimate_usage_cost(response.token_usage, input_per_million_tokens=INPUT_PRICE, cached_input_per_million_tokens=CACHED_INPUT_PRICE, output_per_million_tokens=OUTPUT_PRICE)


class State:
    def __init__(self, ecology: str, seed: int, cell: dict[str, Any]):
        self.ecology, self.seed, self.cell = ecology, seed, cell
        self.memories: list[list[dict[str, Any]]] = [[] for _ in range(NUM_AGENTS)]
        self.alpha = [[1.0 for _ in range(N_NICHES)] for _ in range(NUM_AGENTS)]
        self.beta = [[7.0 for _ in range(N_NICHES)] for _ in range(NUM_AGENTS)]

    def mu(self, niche: int) -> list[float]:
        return [self.alpha[i][niche] / (self.alpha[i][niche] + self.beta[i][niche]) for i in range(NUM_AGENTS)]

    def add_feedback(self, selected: int, task: dict[str, Any], correct: bool, t: int, share_u: Sequence[float]) -> list[int]:
        niche = int(task["niche"])
        if correct: self.alpha[selected][niche] += 1
        else: self.beta[selected][niche] += 1
        recipients = [selected] + [agent for agent in range(NUM_AGENTS) if agent != selected and float(share_u[agent]) < float(self.cell["q_share"])]
        item = dict(task); item["seed"] = self.seed; item["role"] = "online"; item["niche"] = niche
        for agent in recipients:
            self.memories[agent].append(item)
            if len(self.memories[agent]) > int(self.cell["k"]): del self.memories[agent][:-int(self.cell["k"])]
        return recipients


def _route(mu: Sequence[float], beta: float, epsilon: float, u: float) -> int:
    values = [math.exp(beta * value - max(beta * v for v in mu)) for value in mu]
    total = sum(values); probabilities = [(1 - epsilon) * value / total + epsilon / NUM_AGENTS for value in values]
    cumulative = 0.0
    for i, probability in enumerate(probabilities):
        cumulative += probability
        if u < cumulative or i == NUM_AGENTS - 1: return i
    return NUM_AGENTS - 1


async def _completion(backend: DeepSeekDirectBackend, *, task: dict[str, Any], ecology: str, logical_id: str, memory: Sequence[dict[str, Any]], events_path: Path, semaphore: asyncio.Semaphore, attempts: dict[str, int], append_lock: asyncio.Lock) -> dict[str, Any]:
    prompt = render_user(ecology, task, memory); attempt = attempts.get(logical_id, 0)
    while attempt < MAX_ATTEMPTS:
        _budget_change(reserve=RESERVATION_USD)
        try:
            async with semaphore:
                response = await backend.complete(system_prompt=SYSTEM_PROMPT, user_prompt=prompt, model=MODEL, model_parameters={"thinking": THINKING, "max_tokens": MAX_TOKENS})
        except Exception:
            _budget_change(release=RESERVATION_USD); raise
        cost = _cost(response)
        if cost is None: _budget_change(release=RESERVATION_USD); raise RuntimeError("MACRO usage/cost unavailable")
        _budget_change(release=RESERVATION_USD, actual=cost)
        decisions, parse_category = learner.parse_decisions(response.raw_response); provider = response.provider_metadata or {}
        if provider.get("model") != MODEL: raise RuntimeError(f"MACRO model identity changed: {provider.get('model')!r}")
        category = response.error_category or parse_category; error = response.error or parse_category; terminal = decisions is not None or category == "out_of_domain"
        event = {"protocol": PROTOCOL, "event": "completion", "logical_id": logical_id, "attempt": attempt, "ecology": ecology, "task": task, "memory": list(memory), "decisions": decisions, "expected": task.get("y"), "correct": bool(decisions is not None and decisions == task.get("y")), "error": error, "error_category": category, "terminal": terminal, "raw_model_response": response.raw_response, "latency_s": response.latency_s, "token_usage": response.token_usage, "provider_metadata": provider, "attempt_cost_usd": cost, "finished_at_utc": now()}
        async with append_lock: append_jsonl(events_path, event)
        if terminal: return event
        if not response.retryable or category not in RETRYABLE: raise RuntimeError(f"non-retryable MACRO response: {category}")
        attempt += 1; attempts[logical_id] = attempt
    raise RuntimeError(f"MACRO retry exhaustion {logical_id}")


def _lid(phase: str, ecology: str, seed: int, cell_id: str, checkpoint: int, agent: int, niche: int, probe: int | None = None, t: int | None = None) -> str:
    return stable_hash({"protocol": PROTOCOL, "phase": phase, "ecology": ecology, "seed": seed, "cell": cell_id, "checkpoint": checkpoint, "agent": agent, "niche": niche, "probe": probe, "t": t})


def _probe(ecology: str, seed: int, spec: dict[str, Any], niche: int, index: int, checkpoint: int) -> dict[str, Any]:
    x = tuple(spec["evaluation_x"][index]); resolved = _constructor(ecology).resolved(seed, niche, x, "evaluation")
    return {"niche": niche, "x": list(x), "y": list(resolved.y), "template_id": int(resolved.template_id), "role": "evaluation", "probe_index": index, "checkpoint": checkpoint, "seed": seed}


async def run_macro(*, confirm_real: bool = False, concurrency: int = CONCURRENCY) -> dict[str, Any]:
    if not confirm_real: raise SystemExit("Theory V1 MACRO execution requires --confirm-real")
    prediction_path = REPORT_ROOT / "prediction_manifest.json"
    if not prediction_path.exists(): raise RuntimeError("prediction seal is required before MACRO")
    prediction = json.loads(prediction_path.read_text(encoding="utf-8"))
    if prediction.get("status") != "PREDICTIONS_GENERATED_AFTER_MICRO": raise RuntimeError("prediction manifest is not sealed after MICRO")
    manifest = json.loads(MACRO_REPORT.read_text(encoding="utf-8"))
    if manifest.get("manifest_hash") != stable_hash({k: v for k, v in manifest.items() if k != "manifest_hash"}): raise RuntimeError("MACRO manifest integrity failure")
    events_path = MACRO_ROOT / "macro_events.jsonl"; status_path = MACRO_ROOT / "macro_status.json"; events = learner._load_events(events_path)
    terminal = {e["logical_id"]: e for e in events if e.get("event") == "completion" and e.get("terminal")}; attempts = collections.Counter(e["logical_id"] for e in events if e.get("event") == "completion")
    status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {"protocol": PROTOCOL, "status": "initialized", "manifest_hash": manifest["manifest_hash"], "logical_calls": manifest["logical_calls"], "created_at_utc": now()}
    if status.get("manifest_hash") != manifest["manifest_hash"]: raise RuntimeError("MACRO status/manifest mismatch")
    status.update(status="running", started_or_resumed_at_utc=now()); atomic_json(status_path, status)
    states = {(ecology, int(seed), int(cell["cell_id"])): State(ecology, int(seed), cell) for ecology in ECOLOGIES for seed in manifest["social_seeds"][ecology] for cell in manifest["cells"]}
    step_events = [e for e in events if e.get("event") == "online_step"]
    if not step_events:
        step_events = learner._load_events(MACRO_ROOT / "macro_steps.jsonl")
    for e in step_events:
        state = states[(e["ecology"], int(e["seed"]), int(e["cell_id"]))]
        state.add_feedback(int(e["selected_agent"]), e["task"], bool(e["correct"]), int(e["t"]), e["sharing_u"])
    backend = None; semaphore = asyncio.Semaphore(concurrency); append_lock = asyncio.Lock()
    try:
        key = CredentialStore().get(source="keychain"); backend = DeepSeekDirectBackend(api_key=key, thinking=THINKING, max_tokens=MAX_TOKENS, max_connections=concurrency, max_keepalive_connections=concurrency)
        # Common t0 is one set per ecology/seed and is intentionally shared by all cells.
        for ecology in ECOLOGIES:
            for seed in manifest["social_seeds"][ecology]:
                spec = manifest["seed_specs"][f"{ecology}:{seed}"]
                for agent in range(NUM_AGENTS):
                    for niche in range(N_NICHES):
                        for probe_index in range(PROBES_PER_NICHE):
                            task = _probe(ecology, int(seed), spec, niche, probe_index, 0); lid = _lid("t0", ecology, int(seed), "COMMON_T0", 0, agent, niche, probe_index)
                            if lid in terminal: continue
                            result = await _completion(backend, task=task, ecology=ecology, logical_id=lid, memory=[], events_path=events_path, semaphore=semaphore, attempts=attempts, append_lock=append_lock); terminal[lid] = result
        for cell in manifest["cells"]:
            for ecology in ECOLOGIES:
                for seed in manifest["social_seeds"][ecology]:
                    spec = manifest["seed_specs"][f"{ecology}:{seed}"]; state = states[(ecology, int(seed), int(cell["cell_id"]))]
                    existing_step_ids = {str(e.get("logical_id")) for e in step_events}
                    for t, task in enumerate(spec["online"], 1):
                        lid = _lid("online", ecology, int(seed), str(cell["cell_id"]), t, -1, int(task["niche"]), t=t)
                        niche = int(task["niche"]); mu = state.mu(niche); selected = _route(mu, float(cell["beta"]), float(cell["epsilon"]), float(spec["routing_u"][t - 1])); chosen = terminal[lid] if lid in terminal else await _completion(backend, task=task, ecology=ecology, logical_id=lid, memory=state.memories[selected], events_path=events_path, semaphore=semaphore, attempts=attempts, append_lock=append_lock); terminal[lid] = chosen
                        step_id = stable_hash({"lid": lid, "event": "online_step"})
                        if step_id in existing_step_ids:
                            continue
                        recipients = state.add_feedback(selected, task, bool(chosen.get("correct")), t, spec["sharing_u"][t - 1]); step_event = {"protocol": PROTOCOL, "event": "online_step", "logical_id": stable_hash({"lid": lid, "event": "online_step"}), "ecology": ecology, "seed": int(seed), "cell_id": int(cell["cell_id"]), "t": t, "task": task, "selected_agent": selected, "mu_before": mu, "routing_u": spec["routing_u"][t - 1], "sharing_u": spec["sharing_u"][t - 1], "recipients": recipients, "decisions": chosen.get("decisions"), "correct": chosen.get("correct"), "finished_at_utc": now()}; append_jsonl(events_path, step_event); append_jsonl(MACRO_ROOT / "macro_steps.jsonl", step_event)
                        existing_step_ids.add(step_id)
                    for checkpoint in MACRO_CHECKPOINTS[1:]:
                        if checkpoint != t: continue
                        pending = []
                        for agent in range(NUM_AGENTS):
                            for niche in range(N_NICHES):
                                for probe_index in range(PROBES_PER_NICHE):
                                    task_probe = _probe(ecology, int(seed), spec, niche, probe_index, checkpoint); lid_probe = _lid("checkpoint", ecology, int(seed), str(cell["cell_id"]), checkpoint, agent, niche, probe_index)
                                    if lid_probe not in terminal: pending.append((lid_probe, agent, task_probe, list(state.memories[agent])))
                        results = await asyncio.gather(*[_completion(backend, task=task_probe, ecology=ecology, logical_id=lid_probe, memory=memory, events_path=events_path, semaphore=semaphore, attempts=attempts, append_lock=append_lock) for lid_probe, agent, task_probe, memory in pending])
                        for (lid_probe, agent, task_probe, memory), result in zip(pending, results): terminal[lid_probe] = result; append_jsonl(MACRO_ROOT / "macro_checkpoint_observations.jsonl", {"protocol": PROTOCOL, "event": "checkpoint_observation", "logical_id": lid_probe, "ecology": ecology, "seed": int(seed), "cell_id": int(cell["cell_id"]), "checkpoint": checkpoint, "agent": agent, "niche": task_probe["niche"], "probe_index": task_probe["probe_index"], "memory_hash": stable_hash(memory), "memory_hash_after": stable_hash(state.memories[agent]), "no_mutation": stable_hash(memory) == stable_hash(state.memories[agent]), "correct": result.get("correct"), "finished_at_utc": now()})
        final_events = learner._load_events(events_path); final_terminal = {e["logical_id"] for e in final_events if e.get("event") == "completion" and e.get("terminal")}
        if len(final_terminal) != manifest["logical_calls"]: raise RuntimeError(f"MACRO coverage {len(final_terminal)}/{manifest['logical_calls']}")
        status.update(status="completed", logical_calls=len(final_terminal), physical_attempts=len([e for e in final_events if e.get("event") == "completion"]), retries=sum(int(e.get("attempt", 0)) for e in final_events if e.get("event") == "completion"), observed_cost_usd=sum(float(e.get("attempt_cost_usd") or 0.0) for e in final_events if e.get("event") == "completion"), finished_at_utc=now())
    except Exception as exc:
        status.update(status="incomplete", failure=f"{type(exc).__name__}: {exc}", finished_at_utc=now()); raise
    finally:
        if backend is not None: await backend.close()
        atomic_json(status_path, status)
    return status


def health() -> dict[str, Any]:
    manifest = json.loads(MACRO_REPORT.read_text(encoding="utf-8")); all_events = learner._load_events(MACRO_ROOT / "macro_events.jsonl"); events = [e for e in all_events if e.get("event") == "completion"]
    terminal = {e["logical_id"] for e in events if e.get("terminal")}; errors = collections.Counter(e.get("error_category") for e in events if e.get("error_category")); cost = sum(float(e.get("attempt_cost_usd") or 0.0) for e in events)
    return {"protocol": PROTOCOL, "logical_expected": manifest["logical_calls"], "logical_terminal": len(terminal), "physical_attempts": len(events), "technical_retries": sum(int(e.get("attempt", 0)) for e in events), "error_categories": dict(errors), "coverage": len(terminal) / manifest["logical_calls"], "observed_cost_usd": cost, "models": sorted({(e.get("provider_metadata") or {}).get("model") for e in events}), "classification": "CLEAN" if len(terminal) == manifest["logical_calls"] and not any(int(e.get("attempt", 0)) for e in events) else ("COMPLETE_WITH_RETRIES" if len(terminal) == manifest["logical_calls"] else "INCOMPLETE")}
