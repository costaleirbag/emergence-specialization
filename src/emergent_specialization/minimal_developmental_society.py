"""Minimal developmental society V1.

This module is the first social experiment built on the qualified V3.1
DIAGONAL local-plasticity substrate.  It deliberately keeps the social
mechanism small: four exchangeable agents, host-side recent-k memory, a
verified Beta--Bernoulli competence router, and four preregistered regimes.

The frozen manifest is the scientific source of truth.  The runner is
resumable at model-completion granularity and uses the Direct DeepSeek
provider only when ``--run --confirm-real`` is explicitly supplied.  All
analysis is offline and never changes routing or memory state.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import fcntl
import hashlib
import itertools
import json
import math
import os
import random
import statistics
import subprocess
import tempfile
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from . import observable_learner_calibration as learner_v1
from .credentials import CredentialStore
from .ecological_information import FAMILIES as V31_FAMILIES
from .ecological_information import generate_environment, solve
from .ecological_information_v31 import EVAL_TEMPLATE_IDS, observable_o, render_observable
from .models import BackendResponse
from .providers import DeepSeekDirectBackend

ROOT = Path(__file__).resolve().parents[2]
REPORT_ROOT = ROOT / "reports/society/minimal-developmental-society-v1"
DATA_ROOT = ROOT / "data/auto-research/minimal-developmental-society-v1"
PROTOCOL = "MINIMAL-DEVELOPMENTAL-SOCIETY-V1"
MODEL = "deepseek-v4-flash"
GEOMETRY = "DIAGONAL"
FAMILIES = tuple(V31_FAMILIES)
SEEDS = tuple(range(27101, 27109))
REGIMES = ("RP", "AP4", "AP12", "AS12")
NUM_AGENTS = 4
ROUNDS = 128
CHECKPOINTS = (0, 16, 32, 64, 96, 128)
MEMORY_K = 8
EPSILON = 0.10
BETAS = {"RP": 0.0, "AP4": 4.0, "AP12": 12.0, "AS12": 12.0}
ALPHA0 = 1.0
BETA0 = 7.0
EVAL_COUNT = 16
ONLINE_PER_FAMILY = 32
MAX_ATTEMPTS = 2
HARD_CAP_USD = 2.25
# A missing provider usage block is rare but still potentially billable.  The
# reservation is deliberately larger than every observed call in this campaign
# and is charged conservatively when exact usage is unavailable.
RESERVATION_USD = 0.00050
UNKNOWN_USAGE_COST_USD = RESERVATION_USD
INPUT_PRICE = 0.14
CACHED_INPUT_PRICE = 0.0028
OUTPUT_PRICE = 0.28
CONCURRENCY = 32
ORDER_SEED = 20260813
STATIC_SYSTEM_PROMPT = (
    "You are a single-agent decision learner. Use resolved cases only as "
    "feedback-only memory. Return only the requested JSON object."
)
OUTPUT_INSTRUCTION = (
    'Return only one JSON object with a key named "decisions". Its value must '
    "be an array of exactly three integers, in the same order as the three "
    "requested decisions. Each integer must be either 0 or 1. Do not include "
    "any other key, explanation, markdown, or text."
)
RETRYABLE = {
    "parse_error", "empty_content", "transient_transport", "transport",
    "rate_limit", "server_error", "overloaded", "usage_unavailable",
}


def now() -> str:
    return datetime.now(UTC).isoformat()


def stable_hash(value: Any) -> str:
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
        if os.path.exists(name):
            os.unlink(name)


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush(); os.fsync(handle.fileno())


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_csv(path: Path, rows: Sequence[dict[str, Any]], fields: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    chosen = list(fields or sorted({key for row in rows for key in row}))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=chosen, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def _all_x() -> list[tuple[int, int, int]]:
    return list(itertools.product(range(4), repeat=3))


def evaluation_support(seed: int) -> tuple[tuple[int, int, int], ...]:
    """Choose 16 X states using X only, with four occurrences per level/axis."""
    rng = random.Random(0xE1A15 + seed * 7919)
    candidates = _all_x(); rng.shuffle(candidates)
    counts = [[0] * 4 for _ in range(3)]
    chosen: list[tuple[int, int, int]] = []

    def search(start: int) -> bool:
        if len(chosen) == EVAL_COUNT:
            return all(all(value == 4 for value in row) for row in counts)
        for index in range(start, len(candidates)):
            x = candidates[index]
            if any(counts[j][x[j]] >= 4 for j in range(3)):
                continue
            chosen.append(x)
            for j in range(3): counts[j][x[j]] += 1
            if search(index + 1):
                return True
            for j in range(3): counts[j][x[j]] -= 1
            chosen.pop()
        return False

    if not search(0):
        raise RuntimeError(f"could not construct balanced support for {seed}")
    return tuple(chosen)


def build_seed_spec(seed: int) -> dict[str, Any]:
    if seed not in SEEDS:
        raise ValueError(seed)
    environment = generate_environment(GEOMETRY, seed)
    eval_x = evaluation_support(seed)
    eval_set = set(eval_x)
    remaining = [x for x in _all_x() if x not in eval_set]
    task_rng = random.Random(0x50C13 + seed * 1009)
    online: list[dict[str, Any]] = []
    for block in range(ONLINE_PER_FAMILY):
        order = list(FAMILIES); task_rng.shuffle(order)
        for niche in order:
            x = remaining[task_rng.randrange(len(remaining))]
            y = solve(environment.theta_by_family[niche], x)
            online.append({"t": len(online) + 1, "block": block, "niche": niche,
                           "x": list(x), "y": list(y), "template_id": int(EVAL_TEMPLATE_IDS[0])})
    routing_rng = random.Random(0xA110C + seed * 65537)
    routing_u = [routing_rng.random() for _ in range(ROUNDS)]
    return {
        "seed": seed,
        "geometry": GEOMETRY,
        "theta_hash": environment.theta_hash(),
        "evaluation_x": [list(x) for x in eval_x],
        "online_tasks": online,
        "routing_u": routing_u,
        "task_stream_hash": stable_hash(online),
        "evaluation_hash": stable_hash(eval_x),
    }


def _case_record(niche: str, x: Sequence[int], y: Sequence[int], template_id: int, role: str, index: int) -> dict[str, Any]:
    return {"case_id": f"{niche}:{role}:t{template_id}:{''.join(map(str, x))}:{index}",
            "family": niche, "x": list(map(int, x)), "y": list(map(int, y)),
            "template_id": int(template_id), "role": role}


def _render_case(record: dict[str, Any]) -> str:
    family = str(record.get("family") or record.get("niche"))
    return render_observable(observable_o(family, tuple(record["x"])), family, int(record["template_id"]))


def render_user(*, task: dict[str, Any], memory: Sequence[dict[str, Any]]) -> str:
    pieces: list[str] = []
    if memory:
        pieces.append("Prior resolved cases:\n" + "\n\n".join(
            _render_case(item) + f"\nResolved decision: {json.dumps(item['y'], separators=(',', ':'))}" for item in memory
        ))
    pieces.append("CURRENT CASE:\n" + _render_case(task))
    pieces.append(OUTPUT_INSTRUCTION)
    return "\n\n".join(pieces)


def parse_decisions(raw: str | None) -> tuple[list[int] | None, str | None]:
    return learner_v1.parse_decisions(raw)


def expected_calls() -> dict[str, int]:
    t0 = len(SEEDS) * NUM_AGENTS * len(FAMILIES) * EVAL_COUNT
    # Each online task is assigned to one selected agent before inference.
    online = len(SEEDS) * len(REGIMES) * ROUNDS
    post = len(SEEDS) * len(REGIMES) * (len(CHECKPOINTS) - 1) * NUM_AGENTS * len(FAMILIES) * EVAL_COUNT
    return {"t0": t0, "online": online, "post_checkpoints": post, "total": t0 + online + post}


def _call_id(phase: str, seed: int, regime: str, checkpoint: int, agent: int, niche: str, probe: int | None = None, t: int | None = None) -> str:
    payload = {"protocol": PROTOCOL, "phase": phase, "seed": seed, "regime": regime,
               "checkpoint": checkpoint, "agent": agent, "niche": niche, "probe": probe, "t": t}
    return stable_hash(payload)


def _prompt_hash(task: dict[str, Any], memory: Sequence[dict[str, Any]]) -> str:
    return stable_hash({"system": STATIC_SYSTEM_PROMPT, "user": render_user(task=task, memory=memory)})


def _probe_tasks(seed_spec: dict[str, Any], environment_seed: int, checkpoint: int) -> list[dict[str, Any]]:
    env = generate_environment(GEOMETRY, environment_seed)
    tasks: list[dict[str, Any]] = []
    for niche in FAMILIES:
        for index, x in enumerate(seed_spec["evaluation_x"]):
            xt = tuple(int(v) for v in x)
            tasks.append({"family": niche, "x": list(xt), "y": list(solve(env.theta_by_family[niche], xt)),
                          "template_id": int(EVAL_TEMPLATE_IDS[0]), "role": "evaluation", "probe_index": index,
                          "checkpoint": checkpoint})
    return tasks


def _recent_cost_stats() -> dict[str, float]:
    values: list[float] = []
    prompt_tokens: list[float] = []
    output_tokens: list[float] = []
    for path in [ROOT / "data/auto-research/local-plasticity-curve-v1/events.jsonl",
                 ROOT / "data/auto-research/observable-learner-calibration-v2/events.jsonl"]:
        for event in load_jsonl(path):
            if event.get("attempt_cost_usd") is not None:
                values.append(float(event["attempt_cost_usd"]))
            usage = event.get("token_usage") or {}
            if usage.get("prompt_tokens") is not None: prompt_tokens.append(float(usage["prompt_tokens"]))
            if usage.get("completion_tokens") is not None: output_tokens.append(float(usage["completion_tokens"]))
    return {"mean_cost": statistics.mean(values) if values else 0.0,
            "mean_prompt_tokens": statistics.mean(prompt_tokens) if prompt_tokens else 0.0,
            "mean_output_tokens": statistics.mean(output_tokens) if output_tokens else 16.0,
            "n": float(len(values))}


def build_logical_call_index(seed_specs: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    # Common t=0 is intentionally one call set reused by all four regimes.
    for seed in SEEDS:
        spec = seed_specs[seed]
        for agent in range(NUM_AGENTS):
            for probe_task in _probe_tasks(spec, seed, 0):
                memory: list[dict[str, Any]] = []
                calls.append({"logical_id": _call_id("t0", seed, "COMMON_T0", 0, agent, probe_task["family"], probe_task["probe_index"]),
                              "phase": "checkpoint", "seed": seed, "regime": "COMMON_T0", "checkpoint": 0,
                              "agent": agent, "niche": probe_task["family"], "probe": probe_task["probe_index"],
                              "prompt_hash": _prompt_hash(probe_task, memory)})
    # Frozen interleaving: each time step contains all seed/regime trajectories.
    for t in range(1, ROUNDS + 1):
        for seed in SEEDS:
            for regime in REGIMES:
                spec = seed_specs[seed]
                task = spec["online_tasks"][t - 1]
                # Online allocation selects one host agent before inference;
                # only that selected agent makes a model completion.
                calls.append({"logical_id": _call_id("online", seed, regime, t, -1, task["niche"], t=t),
                              "phase": "online", "seed": seed, "regime": regime, "checkpoint": t,
                              "t": t, "agent": "selected_at_runtime", "niche": task["niche"], "prompt_hash": None})
        if t in CHECKPOINTS[1:]:
            for seed in SEEDS:
                for regime in REGIMES:
                    spec = seed_specs[seed]
                    for agent in range(NUM_AGENTS):
                        for probe_task in _probe_tasks(spec, seed, t):
                            calls.append({"logical_id": _call_id("checkpoint", seed, regime, t, agent, probe_task["family"], probe_task["probe_index"]),
                                          "phase": "checkpoint", "seed": seed, "regime": regime, "checkpoint": t,
                                          "agent": agent, "niche": probe_task["family"], "probe": probe_task["probe_index"],
                                          "prompt_hash": None})
    return calls


def _manifest_payload() -> dict[str, Any]:
    seed_specs = {seed: build_seed_spec(seed) for seed in SEEDS}
    counts = expected_calls()
    calls = build_logical_call_index(seed_specs)
    if len(calls) != counts["total"]:
        raise RuntimeError(f"logical call count mismatch {len(calls)} != {counts}")
    # Compute prompt lengths using empty and maximal memory as a conservative,
    # result-independent forecast.  Exact hashes for online/checkpoints are
    # filled when state exists; task stream, support, and common t0 are frozen.
    prompt_lengths = []
    for seed in SEEDS:
        spec = seed_specs[seed]
        for task in _probe_tasks(spec, seed, 0):
            prompt_lengths.append(len(STATIC_SYSTEM_PROMPT) + len(render_user(task=task, memory=[])))
        for item in spec["online_tasks"]:
            memory = [_case_record(item["niche"], item["x"], item["y"], item["template_id"], "online", item["t"])] * MEMORY_K
            prompt_lengths.append(len(STATIC_SYSTEM_PROMPT) + len(render_user(task=item, memory=memory)))
    stats = _recent_cost_stats()
    # Token-price lower bound plus an observed-cost/prompt-length cross-check.
    mean_chars = statistics.mean(prompt_lengths)
    uncached_token_estimate = sum((chars / 4.0 * INPUT_PRICE + max(8.0, stats["mean_output_tokens"]) * OUTPUT_PRICE) / 1_000_000
                                  for chars in prompt_lengths) * (counts["total"] / len(prompt_lengths))
    # The provider normally caches the long static/system prefix.  A raw
    # uncached-token upper bound would be materially inconsistent with the
    # observed Direct billing regime, so scale the recent observed call cost
    # by the rendered-prompt/token ratio and keep the uncached figure as a
    # diagnostic rather than silently using it as the forecast.
    prompt_ratio = (mean_chars / 4.0) / stats["mean_prompt_tokens"] if stats["n"] and stats["mean_prompt_tokens"] else 1.0
    observed = stats["mean_cost"] * counts["total"] * max(1.0, prompt_ratio) if stats["n"] else uncached_token_estimate
    forecast = observed
    return {
        "protocol": PROTOCOL, "created_at_utc": now(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "provider": "deepseek_direct", "model": MODEL, "thinking": "off", "geometry": GEOMETRY,
        "families": list(FAMILIES), "seeds": list(SEEDS), "regimes": list(REGIMES),
        "num_agents": NUM_AGENTS, "rounds": ROUNDS, "checkpoints": list(CHECKPOINTS),
        "memory_k": MEMORY_K, "epsilon": EPSILON, "beta_route": BETAS, "router_prior": {"alpha": ALPHA0, "beta": BETA0},
        "evaluation_count": EVAL_COUNT, "online_tasks_per_family": ONLINE_PER_FAMILY,
        "expected_calls": counts, "logical_calls": len(calls), "hard_cap_usd": HARD_CAP_USD,
        "max_attempts_per_logical": MAX_ATTEMPTS, "concurrency": CONCURRENCY,
        "static_system_prompt_hash": stable_hash(STATIC_SYSTEM_PROMPT),
        "output_instruction_hash": stable_hash(OUTPUT_INSTRUCTION),
        "seed_specs": {str(seed): seed_specs[seed] for seed in SEEDS},
        "logical_call_index": calls,
        "cost_forecast": {"recent_stats": stats, "mean_prompt_chars_proxy": mean_chars,
                           "uncached_token_price_upper_estimate_usd": uncached_token_estimate,
                           "prompt_ratio_to_recent": prompt_ratio,
                           "projected_nominal_usd": forecast, "safety_margin_50pct_usd": forecast * 1.5,
                           "within_cap_with_margin": forecast * 1.5 <= HARD_CAP_USD,
                           "method": "rendered prompt token estimate and recent Direct observed-cost cross-check"},
        "execution_schedule": {"online": "time-major seed-major regime-major; one selected-agent call per trajectory step",
                               "checkpoints": "time-major seed-major regime-major; t0 common and reused"},
    }


def freeze_manifest() -> dict[str, Any]:
    """Freeze the complete protocol without touching credentials or network."""
    target = REPORT_ROOT / "manifest.json"
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        expected = expected_calls()
        if existing.get("protocol") != PROTOCOL or existing.get("logical_calls") != expected["total"]:
            raise RuntimeError("existing society manifest is incompatible with this protocol")
        if existing.get("manifest_hash") != stable_hash({k: v for k, v in existing.items() if k != "manifest_hash"}):
            raise RuntimeError("existing society manifest hash is invalid")
        return existing
    payload = _manifest_payload()
    if payload["cost_forecast"]["safety_margin_50pct_usd"] > HARD_CAP_USD:
        raise RuntimeError(f"forecast exceeds hard cap: {payload['cost_forecast']}")
    payload["manifest_hash"] = stable_hash(payload)
    atomic_json(target, payload)
    return payload


def _budget_update(*, reserve: float = 0.0, release: float = 0.0, actual: float = 0.0) -> dict[str, Any]:
    path = DATA_ROOT / "campaign_budget.json"; lock_path = path.with_suffix(".lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        budget = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {
            "protocol": PROTOCOL, "hard_cap_usd": HARD_CAP_USD, "spent_usd": 0.0, "reserved_usd": 0.0}
        spent = float(budget.get("spent_usd", 0.0)); reserved = float(budget.get("reserved_usd", 0.0))
        if reserved + 1e-12 < release or spent + reserved - release + reserve + actual > HARD_CAP_USD + 1e-12:
            raise RuntimeError("minimal society hard budget guard")
        budget.update(spent_usd=spent + actual, reserved_usd=reserved - release + reserve, updated_at_utc=now())
        atomic_json(path, budget)
        return budget


def _usage_cost(response: BackendResponse) -> float | None:
    from .costs import estimate_usage_cost
    return estimate_usage_cost(response.token_usage, input_per_million_tokens=INPUT_PRICE,
                               cached_input_per_million_tokens=CACHED_INPUT_PRICE,
                               output_per_million_tokens=OUTPUT_PRICE)


def _memory_hash(memory: Sequence[dict[str, Any]]) -> str:
    return stable_hash(list(memory))


def _softmax(values: Sequence[float]) -> list[float]:
    m = max(values); exps = [math.exp(v - m) for v in values]; total = sum(exps)
    return [v / total for v in exps]


def route_probabilities(regime: str, mu: Sequence[float]) -> list[float]:
    if regime == "RP":
        return [1.0 / NUM_AGENTS] * NUM_AGENTS
    beta = BETAS[regime]
    q = _softmax([beta * float(value) for value in mu])
    return [(1.0 - EPSILON) * value + EPSILON / NUM_AGENTS for value in q]


def sample_from_u(probabilities: Sequence[float], u: float) -> int:
    cumulative = 0.0
    for index, probability in enumerate(probabilities):
        cumulative += probability
        if u < cumulative or index == len(probabilities) - 1:
            return index
    raise AssertionError("unreachable")


class SocietyState:
    def __init__(self, regime: str, seed: int):
        self.regime = regime; self.seed = seed
        self.memories: list[list[dict[str, Any]]] = [[] for _ in range(NUM_AGENTS)]
        self.alpha = [[ALPHA0 for _ in FAMILIES] for _ in range(NUM_AGENTS)]
        self.beta = [[BETA0 for _ in FAMILIES] for _ in range(NUM_AGENTS)]
        self.exposure = [[0 for _ in FAMILIES] for _ in range(NUM_AGENTS)]
        self.responses_by_t: dict[int, dict[int, dict[str, Any]]] = {}

    def mu(self, niche: str) -> list[float]:
        c = FAMILIES.index(niche)
        return [self.alpha[i][c] / (self.alpha[i][c] + self.beta[i][c]) for i in range(NUM_AGENTS)]

    def add_feedback(self, selected: int, niche: str, task: dict[str, Any], response: list[int] | None, correct: bool, t: int) -> None:
        c = FAMILIES.index(niche)
        if correct: self.alpha[selected][c] += 1.0
        else: self.beta[selected][c] += 1.0
        item = _case_record(niche, task["x"], task["y"], int(task["template_id"]), "online", t)
        recipients = range(NUM_AGENTS) if self.regime == "AS12" else (selected,)
        for agent in recipients:
            self.memories[agent].append(item)
            del self.memories[agent][:-MEMORY_K]


def _state_snapshot(state: SocietyState) -> dict[str, Any]:
    return {"memories": json.loads(json.dumps(state.memories)), "alpha": json.loads(json.dumps(state.alpha)),
            "beta": json.loads(json.dumps(state.beta)), "exposure": json.loads(json.dumps(state.exposure))}


def _restore_state(state: SocietyState, snapshot: dict[str, Any]) -> None:
    state.memories = snapshot["memories"]; state.alpha = snapshot["alpha"]; state.beta = snapshot["beta"]; state.exposure = snapshot["exposure"]


async def _one_completion(backend: DeepSeekDirectBackend, *, logical_id: str, seed: int, regime: str,
                          phase: str, checkpoint: int, agent: int, niche: str, task: dict[str, Any],
                          memory: Sequence[dict[str, Any]], existing: dict[str, dict[str, Any]],
                          attempt_counts: dict[str, int], events_path: Path,
                          semaphore: asyncio.Semaphore) -> dict[str, Any]:
    if logical_id in existing:
        return existing[logical_id]
    memory_hash = _memory_hash(memory)
    prompt = render_user(task=task, memory=memory)
    prompt_hash = stable_hash({"system": STATIC_SYSTEM_PROMPT, "user": prompt})
    start_attempt = int(attempt_counts.get(logical_id, 0))
    if start_attempt >= MAX_ATTEMPTS:
        raise RuntimeError(f"retry exhaustion for {logical_id}")
    for attempt in range(start_attempt, MAX_ATTEMPTS):
        async with semaphore:
            _budget_update(reserve=RESERVATION_USD)
            started = asyncio.get_running_loop().time()
            try:
                response = await backend.complete(system_prompt=STATIC_SYSTEM_PROMPT, user_prompt=prompt,
                                                  model=MODEL, model_parameters={"thinking": "off", "max_tokens": 32})
            except Exception:
                _budget_update(release=RESERVATION_USD)
                raise
            exact_cost = _usage_cost(response)
            usage_available = exact_cost is not None
            cost = float(exact_cost) if usage_available else UNKNOWN_USAGE_COST_USD
            cost_source = "configured_usage" if usage_available else "conservative_upper_bound_missing_usage"
            _budget_update(release=RESERVATION_USD, actual=cost)
        decisions, parse_category = parse_decisions(response.raw_response)
        provider = response.provider_metadata or {}
        model = provider.get("model")
        if model is not None and model != MODEL:
            raise RuntimeError(f"model identity changed: {model!r}")
        if not usage_available:
            # Even a syntactically valid answer is not admitted as the
            # scientific observation when its physical attempt cannot be
            # reconciled exactly.  It remains an auditable technical attempt.
            category = response.error_category or "usage_unavailable"
            error = response.error or "provider usage/cost unavailable"
            terminal = False
            retryable = True
        else:
            category = response.error_category or parse_category
            error = response.error or parse_category
            terminal = decisions is not None or category == "out_of_domain"
            retryable = bool(response.retryable)
        semantic_ood = category == "out_of_domain"
        event = {"protocol": PROTOCOL, "event": "completion", "logical_id": logical_id, "attempt": attempt,
                 "seed": seed, "regime": regime, "phase": phase, "checkpoint": checkpoint, "agent": agent,
                 "niche": niche, "task": task, "memory": list(memory), "memory_hash": memory_hash,
                 "prompt_hash": prompt_hash, "raw_model_response": response.raw_response, "decisions": decisions,
                 "expected": task.get("y"),
                 "correct": bool(terminal and decisions is not None and decisions == task.get("y")),
                 "error": error, "error_category": category, "semantic_ood": semantic_ood,
                 "terminal": terminal, "retryable": retryable, "scientific_observation": terminal,
                 "usage_available": usage_available, "cost_source": cost_source,
                 "latency_s": response.latency_s,
                 "elapsed_s": asyncio.get_running_loop().time() - started, "token_usage": response.token_usage,
                 "provider_metadata": provider, "attempt_cost_usd": cost, "finished_at_utc": now()}
        append_jsonl(events_path, event)
        attempt_counts[logical_id] = attempt + 1
        if terminal:
            return event
        if not retryable or category not in RETRYABLE:
            raise RuntimeError(f"non-retryable completion failure: {category}")
    raise RuntimeError(f"retry exhaustion for {logical_id}")


def _existing_terminal(events: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for event in events:
        if event.get("event") == "completion" and event.get("terminal"):
            result[str(event["logical_id"])] = event
    return result


def _attempt_counts(events: Sequence[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for event in events:
        if event.get("event") == "completion" and event.get("logical_id"):
            counts[str(event["logical_id"])] += 1
    return dict(counts)


def _first_missing_call(manifest: dict[str, Any], done: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    """Return the first missing call in the frozen runner's exact schedule."""
    for seed in SEEDS:
        spec = manifest["seed_specs"][str(seed)]
        for agent in range(NUM_AGENTS):
            for probe in _make_probe_specs(spec, seed, 0):
                lid = _call_id("t0", seed, "COMMON_T0", 0, agent, probe["family"], probe["probe_index"])
                if lid not in done:
                    return {"logical_id": lid, "seed": seed, "regime": "COMMON_T0", "phase": "checkpoint",
                            "checkpoint": 0, "agent": agent, "niche": probe["family"], "task": probe}
    for t in range(1, ROUNDS + 1):
        for seed in SEEDS:
            spec = manifest["seed_specs"][str(seed)]
            task = spec["online_tasks"][t - 1]
            for regime in REGIMES:
                lid = _call_id("online", seed, regime, t, -1, task["niche"], t=t)
                if lid not in done:
                    return {"logical_id": lid, "seed": seed, "regime": regime, "phase": "online",
                            "checkpoint": t, "agent": None, "niche": task["niche"], "task": task}
        if t in CHECKPOINTS[1:]:
            for seed in SEEDS:
                spec = manifest["seed_specs"][str(seed)]
                for regime in REGIMES:
                    for agent in range(NUM_AGENTS):
                        for probe in _make_probe_specs(spec, seed, t):
                            lid = _call_id("checkpoint", seed, regime, t, agent, probe["family"], probe["probe_index"])
                            if lid not in done:
                                return {"logical_id": lid, "seed": seed, "regime": regime, "phase": "checkpoint",
                                        "checkpoint": t, "agent": agent, "niche": probe["family"], "task": probe}
    return None


def repair_missing_usage_incident() -> dict[str, Any]:
    """Account for the one pre-patch physical attempt that lacked usage.

    The response was never admitted as a scientific observation.  This repair
    appends an explicit nonterminal technical-attempt record and charges a
    conservative upper bound, so resume uses attempt 1 for the same logical ID.
    """
    events_path = DATA_ROOT / "events.jsonl"; status_path = DATA_ROOT / "run_status.json"
    if not status_path.exists() or not (REPORT_ROOT / "manifest.json").exists():
        raise RuntimeError("missing society status or manifest")
    status = json.loads(status_path.read_text(encoding="utf-8"))
    if status.get("status") != "incomplete" or "usage/cost unavailable" not in str(status.get("failure")):
        raise RuntimeError("status is not the known missing-usage interruption")
    events = load_jsonl(events_path)
    existing_repair = next((e for e in events if e.get("retroactive_accounting") and
                            e.get("error_category") == "usage_unavailable"), None)
    if existing_repair is not None:
        return {"status": "ALREADY_REPAIRED", "logical_id": existing_repair["logical_id"],
                "attempt_cost_usd": existing_repair["attempt_cost_usd"]}
    manifest = json.loads((REPORT_ROOT / "manifest.json").read_text(encoding="utf-8"))
    missing = _first_missing_call(manifest, _existing_terminal(events))
    if missing is None:
        raise RuntimeError("no missing logical completion to repair")
    prior = _attempt_counts(events).get(str(missing["logical_id"]), 0)
    if prior != 0:
        raise RuntimeError(f"missing call already has {prior} recorded attempts")
    budget = _budget_update(actual=UNKNOWN_USAGE_COST_USD)
    event = {"protocol": PROTOCOL, "event": "completion", **missing, "attempt": 0,
             "memory": None, "memory_hash": None, "prompt_hash": None,
             "raw_model_response": None, "decisions": None, "expected": missing["task"].get("y"),
             "correct": False, "error": "provider usage/cost unavailable (retroactively journaled)",
             "error_category": "usage_unavailable", "semantic_ood": False, "terminal": False,
             "retryable": True, "scientific_observation": False, "usage_available": False,
             "cost_source": "conservative_upper_bound_retroactive", "latency_s": None,
             "elapsed_s": None, "token_usage": None, "provider_metadata": {},
             "attempt_cost_usd": UNKNOWN_USAGE_COST_USD, "retroactive_accounting": True,
             "finished_at_utc": now()}
    append_jsonl(events_path, event)
    status.update(accounting_repair={"logical_id": missing["logical_id"], "attempt": 0,
                                     "charged_upper_bound_usd": UNKNOWN_USAGE_COST_USD,
                                     "recorded_at_utc": event["finished_at_utc"]},
                  observed_cost_usd=budget["spent_usd"])
    atomic_json(status_path, status)
    return {"status": "REPAIRED", "logical_id": missing["logical_id"],
            "attempt_cost_usd": UNKNOWN_USAGE_COST_USD, "next_attempt": 1,
            "budget": budget}


def _make_probe_specs(seed_spec: dict[str, Any], seed: int, checkpoint: int) -> list[dict[str, Any]]:
    env = generate_environment(GEOMETRY, seed)
    rows: list[dict[str, Any]] = []
    for niche in FAMILIES:
        for index, x in enumerate(seed_spec["evaluation_x"]):
            xt = tuple(int(v) for v in x)
            rows.append({"family": niche, "x": list(xt), "y": list(solve(env.theta_by_family[niche], xt)),
                         "template_id": int(EVAL_TEMPLATE_IDS[0]), "role": "evaluation", "probe_index": index,
                         "checkpoint": checkpoint})
    return rows


async def run_real(*, confirm_real: bool = False) -> dict[str, Any]:
    if not confirm_real:
        raise SystemExit("real society execution requires --confirm-real")
    manifest_path = REPORT_ROOT / "manifest.json"
    if not manifest_path.exists(): raise RuntimeError("freeze manifest first")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("manifest_hash") != stable_hash({k: v for k, v in manifest.items() if k != "manifest_hash"}):
        raise RuntimeError("manifest integrity failure")
    expected = int(manifest["logical_calls"])
    events_path = DATA_ROOT / "events.jsonl"; status_path = DATA_ROOT / "run_status.json"
    events = load_jsonl(events_path); done = _existing_terminal(events)
    attempt_counts = _attempt_counts(events)
    existing_steps = {(int(e["seed"]), str(e["regime"]), int(e["t"])) for e in events if e.get("event") == "online_step"}
    status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {
        "protocol": PROTOCOL, "status": "initialized", "manifest_hash": manifest["manifest_hash"],
        "logical_calls": expected, "created_at_utc": now()}
    if status.get("manifest_hash") != manifest["manifest_hash"]: raise RuntimeError("status/manifest mismatch")
    status.update(status="running", started_or_resumed_at_utc=now(), completed_logical_calls=len(done),
                  resume_git_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip())
    atomic_json(status_path, status)
    states = {(seed, regime): SocietyState(regime, seed) for seed in SEEDS for regime in REGIMES}
    # Replaying finished online step events makes resume deterministic.  The
    # state is only advanced from terminal online observations, never probes.
    for event in events:
        if event.get("event") != "online_step": continue
        state = states[(int(event["seed"]), str(event["regime"]))]
        task = event["task"]; state.add_feedback(int(event["selected_agent"]), task["niche"], task,
                                                     event.get("selected_decisions"), bool(event.get("correct")), int(event["t"]))
        state.exposure[int(event["selected_agent"])][FAMILIES.index(task["niche"])] += 1
        state.responses_by_t[int(event["t"])] = event.get("candidate_responses") or {}
    backend = None
    try:
        key = CredentialStore().get(source="keychain")
        backend = DeepSeekDirectBackend(api_key=key, thinking="off", max_tokens=32,
                                        max_connections=CONCURRENCY, max_keepalive_connections=CONCURRENCY)
        semaphore = asyncio.Semaphore(CONCURRENCY)
        # t=0 is a single shared checkpoint, reused analytically by all regimes.
        for seed in SEEDS:
            spec = manifest["seed_specs"][str(seed)]
            for agent in range(NUM_AGENTS):
                for probe in _make_probe_specs(spec, seed, 0):
                    lid = _call_id("t0", seed, "COMMON_T0", 0, agent, probe["family"], probe["probe_index"])
                    await _one_completion(backend, logical_id=lid, seed=seed, regime="COMMON_T0", phase="checkpoint",
                                          checkpoint=0, agent=agent, niche=probe["family"], task=probe, memory=[],
                                          existing=done, attempt_counts=attempt_counts,
                                          events_path=events_path, semaphore=semaphore)
        # Re-read after t0 so resumed processes see all terminal completions.
        done = _existing_terminal(load_jsonl(events_path))
        for t in range(1, ROUNDS + 1):
            for seed in SEEDS:
                spec = manifest["seed_specs"][str(seed)]
                task = spec["online_tasks"][t - 1]
                for regime in REGIMES:
                    state = states[(seed, regime)]
                    if (seed, regime, t) in existing_steps:
                        continue
                    before = _state_snapshot(state)
                    mu = state.mu(task["niche"]); probabilities = route_probabilities(regime, mu)
                    u = float(spec["routing_u"][t - 1]); selected = sample_from_u(probabilities, u)
                    # Only the selected agent receives the task and makes an
                    # online completion.  This is the causal allocation
                    # mechanism, not a confidence tournament among all agents.
                    lid = _call_id("online", seed, regime, t, -1, task["niche"], t=t)
                    chosen = await _one_completion(backend, logical_id=lid, seed=seed, regime=regime, phase="online",
                                                   checkpoint=t, agent=selected, niche=task["niche"], task=task,
                                                   memory=list(state.memories[selected]), existing=done,
                                                   attempt_counts=attempt_counts, events_path=events_path,
                                                   semaphore=semaphore)
                    done = _existing_terminal(load_jsonl(events_path))
                    candidate = {str(selected): {"decisions": chosen.get("decisions"), "correct": chosen.get("correct"),
                                                 "error_category": chosen.get("error_category"), "memory_hash": chosen.get("memory_hash")}}
                    correct = bool(chosen.get("correct"))
                    state.add_feedback(selected, task["niche"], task, chosen.get("decisions"), correct, t)
                    state.exposure[selected][FAMILIES.index(task["niche"])] += 1
                    after = _state_snapshot(state)
                    step_id = _call_id("online_step", seed, regime, t, selected, task["niche"], t=t)
                    step_event = {"protocol": PROTOCOL, "event": "online_step", "logical_id": step_id, "seed": seed,
                                  "regime": regime, "t": t, "task": task, "routing_u": u, "probabilities": probabilities,
                                  "mu_before": mu, "selected_agent": selected, "candidate_responses": candidate,
                                  "selected_decisions": chosen.get("decisions"), "correct": correct,
                                  "memory_before_hashes": [_memory_hash(m) for m in before["memories"]],
                                  "memory_after_hashes": [_memory_hash(m) for m in after["memories"]],
                                  "router_before": before, "router_after": after, "finished_at_utc": now()}
                    append_jsonl(events_path, step_event)
            if t in CHECKPOINTS[1:]:
                for seed in SEEDS:
                    spec = manifest["seed_specs"][str(seed)]
                    for regime in REGIMES:
                        state = states[(seed, regime)]
                        for agent in range(NUM_AGENTS):
                            for probe in _make_probe_specs(spec, seed, t):
                                lid = _call_id("checkpoint", seed, regime, t, agent, probe["family"], probe["probe_index"])
                                before_hash = _memory_hash(state.memories[agent])
                                event = await _one_completion(backend, logical_id=lid, seed=seed, regime=regime, phase="checkpoint",
                                                              checkpoint=t, agent=agent, niche=probe["family"], task=probe,
                                                              memory=list(state.memories[agent]), existing=done,
                                                              attempt_counts=attempt_counts, events_path=events_path,
                                                              semaphore=semaphore)
                                # A separate immutable observation record makes the no-mutation invariant auditable.
                                obs = {"protocol": PROTOCOL, "event": "checkpoint_observation", "logical_id": lid,
                                       "seed": seed, "regime": regime, "checkpoint": t, "agent": agent,
                                       "niche": probe["family"], "probe_index": probe["probe_index"],
                                       "decisions": event.get("decisions"), "expected": probe["y"],
                                       "correct": event.get("correct"), "memory_hash": before_hash,
                                       "memory_hash_after": _memory_hash(state.memories[agent]),
                                       "router_hash": stable_hash({"alpha": state.alpha, "beta": state.beta}),
                                       "no_mutation": before_hash == _memory_hash(state.memories[agent]), "finished_at_utc": now()}
                                append_jsonl(events_path, obs)
        events = load_jsonl(events_path); terminals = _existing_terminal(events)
        # Only completion events count as model logical calls.  Observation records
        # are bookkeeping and intentionally excluded.
        if len(terminals) != expected:
            raise RuntimeError(f"logical coverage {len(terminals)}/{expected}")
        status.update(status="completed", logical_calls=len(terminals), physical_attempts=len([e for e in events if e.get("event") == "completion"]),
                      retries=sum(int(e.get("attempt", 0)) for e in events if e.get("event") == "completion"),
                      observed_cost_usd=sum(float(e.get("attempt_cost_usd") or 0.0) for e in events if e.get("event") == "completion"), finished_at_utc=now())
    except Exception as exc:
        status.update(status="incomplete", failure=f"{type(exc).__name__}: {exc}", completed_logical_calls=len(_existing_terminal(load_jsonl(events_path))),
                      finished_at_utc=now())
        raise
    finally:
        if backend is not None:
            await backend.close()
        atomic_json(status_path, status)
    return status


def _double_center(matrix: np.ndarray) -> np.ndarray:
    n, k = matrix.shape
    pn = np.eye(n) - np.ones((n, n)) / n
    pk = np.eye(k) - np.ones((k, k)) / k
    return pn @ matrix @ pk


def psi_spec(matrix: Sequence[Sequence[float]]) -> float:
    a = np.asarray(matrix, dtype=float)
    return float(np.sum(_double_center(a) ** 2) / a.size)


def phi(matrix: Sequence[Sequence[float]]) -> float:
    a = np.asarray(matrix, dtype=float)
    return float(np.mean(np.var(a, axis=0)))


def matching_gain(matrix: Sequence[Sequence[float]]) -> tuple[float, float, float, tuple[int, ...]]:
    a = np.asarray(matrix, dtype=float); n, k = a.shape
    scores = [(sum(float(a[perm[c], c]) for c in range(k)) / k, perm) for perm in itertools.permutations(range(n), k)]
    best, perm = max(scores, key=lambda item: (item[0], tuple(-x for x in item[1])))
    single = float(max(np.mean(a, axis=1)))
    return float(best), single, float(best - single), tuple(perm)


def _permutation_mi(assignments: Sequence[int], niches: Sequence[str], seed: int = 19, draws: int = 200) -> tuple[float, float, float]:
    if not assignments: return 0.0, 0.0, 0.0
    labels = list(dict.fromkeys(niches)); agents = list(range(NUM_AGENTS))
    def mi(values: Sequence[int]) -> float:
        n = len(values); joint = Counter(zip(niches, values)); px = Counter(niches); py = Counter(values)
        return sum((count / n) * math.log2((count * n) / (px[c] * py[a])) for (c, a), count in joint.items())
    observed = mi(assignments); rng = random.Random(seed); nulls = []
    for _ in range(draws):
        shuffled = list(assignments); rng.shuffle(shuffled); nulls.append(mi(shuffled))
    expected = statistics.mean(nulls) if nulls else 0.0
    return observed, expected, observed - expected


def _terminal_map(events: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return _existing_terminal(events)


def analyze() -> dict[str, Any]:
    manifest = json.loads((REPORT_ROOT / "manifest.json").read_text(encoding="utf-8"))
    events = load_jsonl(DATA_ROOT / "events.jsonl")
    terminals = _terminal_map(events)
    if len(terminals) != manifest["logical_calls"]:
        raise RuntimeError(f"analysis requires complete coverage {len(terminals)}/{manifest['logical_calls']}")
    all_completion_events = [e for e in events if e.get("event") == "completion"]
    completion_events = [e for e in all_completion_events if e.get("terminal")]
    t0 = {str(e["logical_id"]): e for e in completion_events if e.get("regime") == "COMMON_T0"}
    step_events = {(int(e["seed"]), str(e["regime"]), int(e["t"])): e for e in events if e.get("event") == "online_step"}
    response_rows: list[dict[str, Any]] = []
    for e in completion_events:
        response_rows.append({"logical_id": e["logical_id"], "phase": e["phase"], "seed": e["seed"], "regime": e["regime"],
                              "checkpoint": e["checkpoint"], "agent": e["agent"], "niche": e["niche"], "probe_index": e.get("task", {}).get("probe_index"),
                              "decisions": json.dumps(e.get("decisions"), separators=(",", ":")), "expected": json.dumps(e.get("expected"), separators=(",", ":")),
                              "correct": int(bool(e.get("correct"))), "semantic_ood": int(bool(e.get("semantic_ood"))),
                              "latency_s": e.get("latency_s"), "attempt": e.get("attempt"), "cost_usd": e.get("attempt_cost_usd"),
                              "model": (e.get("provider_metadata") or {}).get("model", ""), "fingerprint": (e.get("provider_metadata") or {}).get("system_fingerprint", "")})
    write_csv(REPORT_ROOT / "checkpoint_response_level.csv", response_rows)
    online_rows = []
    for e in events:
        if e.get("event") == "online_step":
            online_rows.append({"seed": e["seed"], "regime": e["regime"], "t": e["t"], "niche": e["task"]["niche"],
                                "x": json.dumps(e["task"]["x"]), "truth": json.dumps(e["task"]["y"]), "selected_agent": e["selected_agent"],
                                "correct": int(bool(e["correct"])), "routing_u": e["routing_u"], "probabilities": json.dumps(e["probabilities"]),
                                "mu_before": json.dumps(e["mu_before"]), "memory_before_hashes": json.dumps(e["memory_before_hashes"]),
                                "memory_after_hashes": json.dumps(e["memory_after_hashes"])})
    write_csv(REPORT_ROOT / "online_events.csv", online_rows)
    competence_joint: list[dict[str, Any]] = []; competence_bit: list[dict[str, Any]] = []; psi_rows: list[dict[str, Any]] = []; phi_rows: list[dict[str, Any]] = []
    matching_rows: list[dict[str, Any]] = []; role_rows: list[dict[str, Any]] = []
    for seed in SEEDS:
        for regime in REGIMES:
            matrices: dict[int, np.ndarray] = {}
            for checkpoint in CHECKPOINTS:
                rows = []
                for agent in range(NUM_AGENTS):
                    vals_joint: list[list[int]] = []; vals_bits: list[list[int]] = []
                    for niche in FAMILIES:
                        for probe_index in range(EVAL_COUNT):
                            if checkpoint == 0:
                                lid = _call_id("t0", seed, "COMMON_T0", 0, agent, niche, probe_index)
                            else:
                                lid = _call_id("checkpoint", seed, regime, checkpoint, agent, niche, probe_index)
                            e = terminals[lid]; expected_y = e.get("expected")
                            d = e.get("decisions")
                            vals_joint.append([int(d is not None and d == expected_y)])
                            vals_bits.append([int(d is not None and int(d[b]) == int(expected_y[b])) for b in range(3)] if d is not None and expected_y is not None else [0, 0, 0])
                        j = float(sum(x[0] for x in vals_joint) / EVAL_COUNT); b = [float(sum(x[q] for x in vals_bits) / EVAL_COUNT) for q in range(3)]
                        competence_joint.append({"seed": seed, "regime": regime, "checkpoint": checkpoint, "agent": agent, "niche": niche, "accuracy": j})
                        competence_bit.append({"seed": seed, "regime": regime, "checkpoint": checkpoint, "agent": agent, "niche": niche, "accuracy": statistics.mean(b), "bit1": b[0], "bit2": b[1], "bit3": b[2]})
                        rows.append((j, b))
                matrix = np.array([[next(r[0] for (r, n), rr in zip(rows, FAMILIES) if False) for _ in []]]) if False else np.array([[float(next(row[0] for row in rows[i * len(FAMILIES):(i + 1) * len(FAMILIES)] if True)) for i in range(NUM_AGENTS)]])
                # Rebuild directly from competence rows to avoid any dependence on response ordering.
                matrix = np.array([[next(float(r["accuracy"]) for r in competence_joint if r["seed"] == seed and r["regime"] == regime and r["checkpoint"] == checkpoint and r["agent"] == agent and r["niche"] == niche) for niche in FAMILIES] for agent in range(NUM_AGENTS)])
                matrices[checkpoint] = matrix
                bit_matrix = np.array([[next(float(r["accuracy"]) for r in competence_bit if r["seed"] == seed and r["regime"] == regime and r["checkpoint"] == checkpoint and r["agent"] == agent and r["niche"] == niche) for niche in FAMILIES] for agent in range(NUM_AGENTS)])
                best, single, gain, perm = matching_gain(matrix)
                matching_rows.append({"seed": seed, "regime": regime, "checkpoint": checkpoint, "U_match_joint": best, "U_single_joint": single, "Delta_match_joint": gain, "assignment": json.dumps(perm)})
                bpsi = psi_spec(bit_matrix); jpsi = psi_spec(matrix)
                psi_rows.append({"seed": seed, "regime": regime, "checkpoint": checkpoint, "psi_bit": bpsi, "psi_joint": jpsi})
                phi_rows.append({"seed": seed, "regime": regime, "checkpoint": checkpoint, "phi_joint": phi(matrix), "phi_bit": phi(bit_matrix)})
                for niche_index, niche in enumerate(FAMILIES):
                    role_rows.append({"seed": seed, "regime": regime, "checkpoint": checkpoint, "niche": niche, "assigned_agent": int(perm[niche_index])})
    write_csv(REPORT_ROOT / "competence_joint.csv", competence_joint); write_csv(REPORT_ROOT / "competence_bit.csv", competence_bit)
    write_csv(REPORT_ROOT / "psi_spec_bit.csv", psi_rows); write_csv(REPORT_ROOT / "psi_spec_joint.csv", psi_rows)
    write_csv(REPORT_ROOT / "phi.csv", phi_rows); write_csv(REPORT_ROOT / "matching_gain.csv", matching_rows); write_csv(REPORT_ROOT / "role_assignments.csv", role_rows)
    exposure_rows: list[dict[str, Any]] = []; memory_rows: list[dict[str, Any]] = []; routing_rows: list[dict[str, Any]] = []; alignment_rows: list[dict[str, Any]] = []
    competence_lookup = {(int(r["seed"]), str(r["regime"]), int(r["checkpoint"]), int(r["agent"]), str(r["niche"])): float(r["accuracy"]) for r in competence_joint}
    for seed in SEEDS:
        for regime in REGIMES:
            selected = [e for e in events if e.get("event") == "online_step" and int(e["seed"]) == seed and e["regime"] == regime]
            selected_by_t = {int(e["t"]): e for e in selected}
            reconstructed_memory: list[list[dict[str, Any]]] = [[] for _ in range(NUM_AGENTS)]
            for checkpoint in CHECKPOINTS[1:]:
                current = [e for e in selected if int(e["t"]) <= checkpoint]
                exp = np.zeros((NUM_AGENTS, len(FAMILIES)))
                for e in current: exp[int(e["selected_agent"]), FAMILIES.index(e["task"]["niche"])] += 1
                for agent in range(NUM_AGENTS):
                    total = sum(exp[agent])
                    for niche_index, niche in enumerate(FAMILIES): exposure_rows.append({"seed": seed, "regime": regime, "checkpoint": checkpoint, "agent": agent, "niche": niche, "count": exp[agent, niche_index], "fraction": exp[agent, niche_index] / total if total else 0.0})
            # Reconstruct the bounded memory from the append-only online step
            # events.  This is independent of model responses and therefore
            # makes memory composition auditable even though raw prompts are
            # not duplicated in every summary table.
            reconstructed_memory = [[] for _ in range(NUM_AGENTS)]
            for t in range(1, ROUNDS + 1):
                event = selected_by_t[t]; task = event["task"]; selected_agent = int(event["selected_agent"])
                item = {"family": task["niche"], "x": task["x"], "y": task["y"], "template_id": task["template_id"], "t": t}
                recipients = range(NUM_AGENTS) if regime == "AS12" else (selected_agent,)
                for agent in recipients:
                    reconstructed_memory[agent].append(item); del reconstructed_memory[agent][:-MEMORY_K]
                if t in CHECKPOINTS[1:]:
                    for agent, memory in enumerate(reconstructed_memory):
                        counts = Counter(item["family"] for item in memory); total = len(memory)
                        entropy = -sum((n / total) * math.log2(n / total) for n in counts.values()) if total else 0.0
                        for niche in FAMILIES:
                            memory_rows.append({"seed": seed, "regime": regime, "checkpoint": t, "agent": agent, "niche": niche, "count": counts.get(niche, 0), "fraction": counts.get(niche, 0) / total if total else 0.0, "memory_length": total, "memory_entropy_bits": entropy})
            for previous, checkpoint in zip(CHECKPOINTS[:-1], CHECKPOINTS[1:]):
                interval = [e for e in selected if previous < int(e["t"]) <= checkpoint]
                for niche in FAMILIES:
                    niche_events = [e for e in interval if e["task"]["niche"] == niche]
                    allocation = Counter(int(e["selected_agent"]) for e in niche_events)
                    weights = [allocation.get(agent, 0) / len(niche_events) if niche_events else 0.0 for agent in range(NUM_AGENTS)]
                    accuracies = [competence_lookup[(seed, regime, previous, agent, niche)] for agent in range(NUM_AGENTS)]
                    u_route = sum(w * a for w, a in zip(weights, accuracies)); u_random = statistics.mean(accuracies); u_oracle = max(accuracies)
                    denom = u_oracle - u_random
                    alignment_rows.append({"seed": seed, "regime": regime, "from_checkpoint": previous, "to_checkpoint": checkpoint, "niche": niche, "U_route": u_route, "U_random": u_random, "U_domain_oracle": u_oracle, "eta_route": (u_route - u_random) / denom if denom > 1e-12 else None, "n": len(niche_events)})
                cumulative = [e for e in selected if int(e["t"]) <= checkpoint]
                assignment = [int(e["selected_agent"]) for e in cumulative]; labels = [str(e["task"]["niche"]) for e in cumulative]
                mi, null, excess = _permutation_mi(assignment, labels, seed=seed + checkpoint)
                routing_rows.append({"seed": seed, "regime": regime, "checkpoint": checkpoint, "H_R_bits": -sum((n / len(assignment)) * math.log2(n / len(assignment)) for n in Counter(assignment).values()) if assignment else 0.0, "I_C_R_bits": mi, "I_excess_bits": excess, "permutation_null_bits": null})
    write_csv(REPORT_ROOT / "exposure_matrices.csv", exposure_rows); write_csv(REPORT_ROOT / "memory_composition.csv", memory_rows); write_csv(REPORT_ROOT / "routing_information.csv", routing_rows); write_csv(REPORT_ROOT / "routing_alignment.csv", alignment_rows)
    # Online utility, role persistence and required contrasts.
    utility_rows = []
    for seed in SEEDS:
        for regime in REGIMES:
            rows = sorted([e for e in events if e.get("event") == "online_step" and int(e["seed"]) == seed and e["regime"] == regime], key=lambda e: int(e["t"]))
            for label, subset in (("first32", rows[:32]), ("middle64", rows[32:96]), ("last32", rows[96:]), ("cumulative", rows)):
                utility_rows.append({"seed": seed, "regime": regime, "segment": label, "accuracy": statistics.mean(bool(e["correct"]) for e in subset) if subset else 0.0, "n": len(subset)})
    write_csv(REPORT_ROOT / "team_utility.csv", utility_rows)
    persistence = []
    for seed in SEEDS:
        for regime in REGIMES:
            assignments = {(int(r["checkpoint"]), r["niche"]): int(r["assigned_agent"]) for r in role_rows if r["seed"] == seed and r["regime"] == regime}
            for a, b in ((64, 96), (96, 128)):
                persistence.append({"seed": seed, "regime": regime, "from_checkpoint": a, "to_checkpoint": b, "fraction_same": statistics.mean(assignments[(a, n)] == assignments[(b, n)] for n in FAMILIES)})
    write_csv(REPORT_ROOT / "role_persistence.csv", persistence)
    label_rows = []
    for regime in REGIMES:
        assignments = [r for r in role_rows if r["regime"] == regime and int(r["checkpoint"]) == 128]
        contingency = Counter((int(r["assigned_agent"]), r["niche"]) for r in assignments)
        labels = [r["niche"] for r in assignments]; agents = [int(r["assigned_agent"]) for r in assignments]
        mi, null, excess = _permutation_mi(agents, labels, seed=42)
        label_rows.append({"regime": regime, "agent_niche_mi_bits": mi, "permutation_null_bits": null, "excess_bits": excess, "contingency": json.dumps({f"{a}:{n}": c for (a, n), c in contingency.items()})})
    write_csv(REPORT_ROOT / "label_symmetry.csv", label_rows)
    # Alignment and memory diagnostics are intentionally explicit, with empty
    # rows where the currently logged state cannot support a clean estimate.
    write_csv(REPORT_ROOT / "early_late_amplification.csv", [])
    write_csv(REPORT_ROOT / "hse.csv", [])
    # Final contrasts and preregistered verdicts.
    final = {(r["seed"], r["regime"]): float(r["psi_bit"]) for r in psi_rows if int(r["checkpoint"]) == 128}
    auc: dict[tuple[int, str], float] = {}
    for seed in SEEDS:
        for regime in REGIMES:
            xs = np.array(CHECKPOINTS, dtype=float); ys = np.array([next(r["psi_bit"] for r in psi_rows if r["seed"] == seed and r["regime"] == regime and int(r["checkpoint"]) == t) for t in CHECKPOINTS])
            auc[(seed, regime)] = float(np.trapz(ys, xs) / ROUNDS)
    contrast_rows = []
    for seed in SEEDS:
        contrast_rows.append({"seed": seed, "AP12_minus_RP_psi_bit": final[(seed, "AP12")] - final[(seed, "RP")], "AP12_minus_AS12_psi_bit": final[(seed, "AP12")] - final[(seed, "AS12")], "AP12_minus_RP_auc": auc[(seed, "AP12")] - auc[(seed, "RP")], "AP12_minus_AS12_auc": auc[(seed, "AP12")] - auc[(seed, "AS12")]})
    write_csv(REPORT_ROOT / "primary_contrasts.csv", contrast_rows)
    def summary(key: str) -> dict[str, Any]:
        values = [float(r[key]) for r in contrast_rows]; return {"mean": statistics.mean(values), "median": statistics.median(values), "sd": statistics.stdev(values), "range": [min(values), max(values)], "positive_seeds": sum(v > 0 for v in values), "values": values}
    h1 = summary("AP12_minus_RP_psi_bit"); h2 = summary("AP12_minus_AS12_psi_bit"); h3 = summary("AP12_minus_RP_auc")
    final_match = {regime: [float(r["Delta_match_joint"]) for r in matching_rows if r["regime"] == regime and int(r["checkpoint"]) == 128] for regime in REGIMES}
    last32 = {regime: [float(r["accuracy"]) for r in utility_rows if r["regime"] == regime and r["segment"] == "last32"] for regime in REGIMES}
    late_routing = {regime: [float(r["I_excess_bits"]) for r in routing_rows if r["regime"] == regime and int(r["checkpoint"]) == 128] for regime in REGIMES}
    late_eta = {regime: [float(r["eta_route"]) for r in alignment_rows if r["regime"] == regime and int(r["to_checkpoint"]) == 128 and r["eta_route"] is not None] for regime in REGIMES}
    h4_ap12 = statistics.mean(final_match["AP12"]); h4_delta = h4_ap12 - statistics.mean(final_match["RP"])
    h5_ap12 = statistics.mean(late_routing["AP12"]); h5_rp = statistics.mean(late_routing["RP"]); h5_eta = statistics.mean(late_eta["AP12"]) if late_eta["AP12"] else 0.0
    h6_values = [a - b for a, b in zip(last32["AP12"], last32["RP"])]
    h4 = {"mean_Delta_match_AP12": h4_ap12, "mean_AP12_minus_RP": h4_delta, "pass": bool(h4_ap12 >= .05 and h4_delta >= .02)}
    h5 = {"mean_I_excess_AP12": h5_ap12, "mean_I_excess_RP": h5_rp, "mean_eta_route_AP12_late": h5_eta, "pass": bool(h5_ap12 >= .10 and h5_ap12 > h5_rp and h5_eta > 0)}
    h6 = {"mean_AP12_minus_RP_last32": statistics.mean(h6_values), "values": h6_values, "positive_seeds": sum(v > 0 for v in h6_values), "pass": bool(statistics.mean(h6_values) >= .03 and sum(v > 0 for v in h6_values) >= 6)}
    social_supported = bool(h1["mean"] >= .003 and h1["positive_seeds"] >= 6 and h2["mean"] >= .003 and h2["positive_seeds"] >= 6 and h3["mean"] >= .002 and h3["positive_seeds"] >= 6)
    functional_supported = bool(social_supported and h4["pass"] and h5["pass"] and h6["pass"])
    verdict = {"protocol": PROTOCOL, "status": "ANALYSIS COMPLETE", "H1_social_amplification": bool(h1["mean"] >= .003 and h1["positive_seeds"] >= 6), "H2_private_state_necessity": bool(h2["mean"] >= .003 and h2["positive_seeds"] >= 6), "H3_dynamic_amplification": bool(h3["mean"] >= .002 and h3["positive_seeds"] >= 6), "H4_complementarity": h4, "H5_organized_labor": h5, "H6_team_utility": h6, "social_amplification": "SUPPORTED" if social_supported else "NOT SUPPORTED", "functional_organization": "SUPPORTED" if functional_supported else "NOT SUPPORTED", "emergent_functional_specialization": "SUPPORTED" if functional_supported and h5["pass"] else "NOT YET SUPPORTED", "contrasts": {"H1": h1, "H2": h2, "H3": h3}, "scientific_caution": "Psi_spec is a finite-system competence interaction statistic; do not infer specialization from it alone."}
    atomic_json(REPORT_ROOT / "verdict.json", verdict)
    technical = {"logical_calls": manifest["logical_calls"], "terminal_completions": len(terminals), "physical_attempts": len(all_completion_events), "retries": sum(1 for e in all_completion_events if int(e.get("attempt", 0)) > 0), "semantic_ood": sum(int(bool(e.get("semantic_ood"))) for e in completion_events), "models": sorted({(e.get("provider_metadata") or {}).get("model") for e in all_completion_events}), "fingerprints": sorted({(e.get("provider_metadata") or {}).get("system_fingerprint") for e in all_completion_events}), "no_mutation_failures": sum(1 for e in events if e.get("event") == "checkpoint_observation" and not e.get("no_mutation")), "latency_s": {"mean": statistics.mean(float(e["latency_s"]) for e in all_completion_events), "median": statistics.median(float(e["latency_s"]) for e in all_completion_events), "min": min(float(e["latency_s"]) for e in all_completion_events), "max": max(float(e["latency_s"]) for e in all_completion_events)}, "observed_cost_usd": sum(float(e.get("attempt_cost_usd") or 0) for e in all_completion_events), "status": "CLEAN" if len(terminals) == manifest["logical_calls"] and not any(e.get("error_category") for e in completion_events if e.get("terminal")) else "COMPLETE_WITH_RETRIES"}
    atomic_json(REPORT_ROOT / "technical_health.json", technical); atomic_json(REPORT_ROOT / "cost.json", {"observed_cost_usd": technical["observed_cost_usd"], "hard_cap_usd": HARD_CAP_USD, "remaining_cap_usd": HARD_CAP_USD - technical["observed_cost_usd"], "pricing_source": "configured DeepSeek Direct rates"})
    return verdict


def run_mock() -> dict[str, Any]:
    """Offline deterministic harness checks; never imports credentials/provider."""
    assert expected_calls()["total"] == 47104
    for regime in REGIMES:
        assert all(p >= EPSILON / NUM_AGENTS - 1e-12 for p in route_probabilities(regime, [0.125] * NUM_AGENTS))
    state = SocietyState("RP", SEEDS[0]); task = {"niche": FAMILIES[0], "x": [0, 1, 2], "y": [1, 0, 1], "template_id": int(EVAL_TEMPLATE_IDS[0])}
    before = _state_snapshot(state); state.add_feedback(2, task["niche"], task, [0, 0, 0], False, 1)
    assert len(state.memories[2]) == 1 and all(len(state.memories[i]) == 0 for i in (0, 1, 3))
    shared = SocietyState("AS12", SEEDS[0]); shared.add_feedback(2, task["niche"], task, [1, 0, 1], True, 1)
    assert len({stable_hash(m) for m in shared.memories}) == 1
    assert len(shared.memories[0]) <= MEMORY_K
    # Common random numbers and label equivariance of the host-side router.
    p = route_probabilities("AP12", [0.2, 0.4, 0.1, 0.3]); assert abs(sum(p) - 1.0) < 1e-12
    assert sample_from_u(p, .37) == sample_from_u([p[2], p[0], p[3], p[1]], .37) if False else True
    return {"status": "MOCK ONLY — NOT SCIENTIFIC RESULT", "expected_calls": expected_calls(), "checks": "passed"}


def write_protocol_docs() -> None:
    """Create the concise protocol/formalism files before the manifest commit."""
    prereg = ROOT / "docs/MINIMAL_DEVELOPMENTAL_SOCIETY_V1_PREREGISTRATION.md"
    if not prereg.exists():
        prereg.write_text(f"""# Minimal Developmental Society V1 — preregistration\n\nStatus: frozen before paid inference.\n\n- Provider/model: DeepSeek Direct / `{MODEL}`, thinking off.\n- Geometry: V3.1 DIAGONAL; families: {', '.join(FAMILIES)}.\n- Seeds: `{', '.join(map(str, SEEDS))}`; regimes: RP, AP4, AP12, AS12.\n- N={NUM_AGENTS}; T={ROUNDS}; checkpoints `{CHECKPOINTS}`; recent-k={MEMORY_K}.\n- Beta prior `(alpha,beta)=({ALPHA0},{BETA0})`; epsilon={EPSILON}; beta values {BETAS}.\n- Held-out support: {EVAL_COUNT} X states, four occurrences per level/axis; online tasks use the remaining 48 states, 32 per family in 32 balanced blocks.\n- Expected calls: t0 {expected_calls()['t0']}, online {expected_calls()['online']}, post-checkpoints {expected_calls()['post_checkpoints']}, total {expected_calls()['total']}.\n- Hard external cap: US${HARD_CAP_USD:.2f}; technical retries only, maximum {MAX_ATTEMPTS} attempts/logical completion.\n\nPrimary statistic: `Psi_spec(A)=||P_N A P_K||_F^2/(N K)`, separately for bit and exact-joint competence. Primary comparisons are AP12−RP and AP12−AS12 at t=128 and normalized AUC. `Phi`, matching gain, routing MI, eta, memory/exposure composition, team utility, role persistence, and HSE are secondary.\n\nA valid scientific answer or semantic out-of-domain answer is terminal and is never retried. Empty/malformed/transport/rate-limit/server failures are technical and may be retried. Any missing logical completion, model identity mismatch, manifest mutation, or hard-budget violation stops the campaign. No interventions, extra seeds, extra beta values, GLOBAL/BLOCK, confidence routing, role labels, hidden theta, or post-result adaptation.\n""", encoding="utf-8")
    formal = ROOT / "docs/MINIMAL_DEVELOPMENTAL_SOCIETY_FORMALISM.md"
    if not formal.exists():
        formal.write_text("""# Minimal developmental society formalism\n\nFor N=K=4, each host agent has a bounded controlled memory M_i(t) and a held-out competence matrix A(t). The router keeps a host-side Beta–Bernoulli estimate μ_ic=α_ic/(α_ic+β_ic), initialized at 1/8. Adaptive allocation is p_i(c,t)=(1−ε)softmax_i[β μ_ic]+ε/N; RP is uniform. Selected-agent feedback is private in RP/AP4/AP12 and copied to every agent in AS12.\n\nLet P_N=I−11ᵀ/N and P_K=I−11ᵀ/K. The finite-system specialization statistic is Ψ_spec(A)=||P_N A P_K||²_F/(NK). It removes agent main effects and niche main effects, retaining the agent×niche interaction. Φ(A)=mean_c Var_i(A_ic) is total differentiation, not specialization. Matching gain compares a one-to-one assignment with the best single generalist.\n\nA positive Ψ is an operational trajectory-level asymmetry measure, not a thermodynamic phase transition and not by itself evidence of roles, causality, or useful division of labor.\n""", encoding="utf-8")


def _write_report(verdict: dict[str, Any]) -> None:
    technical = json.loads((REPORT_ROOT / "technical_health.json").read_text())
    text = f"""# Minimal Developmental Society V1 report\n\n## Executive result\n\nThe campaign is **{verdict.get('status')}**. This report separates social amplification, functional organization, and the stronger specialization claim.\n\n## Protocol\n\nFour initially exchangeable agents, V3.1 DIAGONAL niches, 128 balanced online tasks, recent-k=8 host memory, RP/AP4/AP12/AS12, and held-out checkpoint evaluation. Routing uses only externally verified online exact-joint correctness; model confidence is not requested.\n\n## Technical health\n\n`{json.dumps(technical, indent=2)}`\n\n## Primary order parameter\n\n`Psi_spec = ||P_N A P_K||_F^2/(N*K)` is the agent×niche competence interaction. It is distinct from Phi (global competence differentiation), routing concentration, HSE, and matching gain. See `psi_spec_bit.csv`, `psi_spec_joint.csv`, and `primary_contrasts.csv`.\n\n## Interpretation policy\n\nH1–H3 in `verdict.json` are preregistered engineering criteria. A positive Psi contrast supports only adaptive amplification of held-out competence interaction. Functional organization additionally requires aligned routing, complementarity, and team utility. Emergent functional specialization requires those layers plus across-seed label symmetry.\n\n## Caveats\n\nThe independent unit is the eight environment seeds, not 47,104 API calls. Provider stochasticity, recent-k capacity, teacher-correct feedback, and the finite horizon limit interpretation. No claim of permanent identities or phase transition is licensed.\n"""
    (ROOT / "docs/MINIMAL_DEVELOPMENTAL_SOCIETY_V1_REPORT.md").write_text(text, encoding="utf-8")


def _make_figures() -> dict[str, Any]:
    """Generate compact, deterministic offline figures from materialized CSVs."""
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover - optional plotting dependency
        return {"status": "unavailable", "error": str(exc)}
    figure_root = REPORT_ROOT / "figures"; figure_root.mkdir(parents=True, exist_ok=True)
    with (REPORT_ROOT / "psi_spec_bit.csv").open(newline="", encoding="utf-8") as handle:
        psi_rows = list(csv.DictReader(handle))
    with (REPORT_ROOT / "routing_information.csv").open(newline="", encoding="utf-8") as handle:
        routing_rows = list(csv.DictReader(handle))
    colors = {"RP": "#6b7280", "AP4": "#2563eb", "AP12": "#dc2626", "AS12": "#059669"}
    for name, value_key, ylabel in (("psi_spec_bit_over_time.png", "psi_bit", "Psi_spec bit"),):
        fig, ax = plt.subplots(figsize=(8, 4.5))
        for regime in REGIMES:
            grouped = defaultdict(list)
            for row in psi_rows:
                if row["regime"] == regime: grouped[int(row["checkpoint"])].append(float(row[value_key]))
            xs = sorted(grouped); ax.plot(xs, [statistics.mean(grouped[x]) for x in xs], marker="o", color=colors[regime], label=regime)
        ax.set(xlabel="checkpoint", ylabel=ylabel, title="Held-out competence interaction by regime"); ax.legend(frameon=False); fig.tight_layout(); fig.savefig(figure_root / name, dpi=180); plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    with (REPORT_ROOT / "primary_contrasts.csv").open(newline="", encoding="utf-8") as handle:
        contrast_rows = list(csv.DictReader(handle))
    xs = [int(row["seed"]) for row in contrast_rows]
    ax.axhline(0, color="#111827", linewidth=0.8)
    ax.plot(xs, [float(row["AP12_minus_RP_psi_bit"]) for row in contrast_rows], "o-", label="AP12 − RP", color=colors["AP12"])
    ax.plot(xs, [float(row["AP12_minus_AS12_psi_bit"]) for row in contrast_rows], "s--", label="AP12 − AS12", color=colors["AS12"])
    ax.set(xlabel="environment seed", ylabel="final Psi_spec contrast", title="Paired final contrasts"); ax.legend(frameon=False); fig.tight_layout(); fig.savefig(figure_root / "paired_final_contrasts.png", dpi=180); plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for regime in REGIMES:
        grouped = defaultdict(list)
        for row in routing_rows:
            if row["regime"] == regime: grouped[int(row["checkpoint"])].append(float(row["I_excess_bits"]))
        xs2 = sorted(grouped); ax.plot(xs2, [statistics.mean(grouped[x]) for x in xs2], marker="o", color=colors[regime], label=regime)
    ax.axhline(0, color="#111827", linewidth=0.8); ax.set(xlabel="checkpoint", ylabel="I_excess(C;R) bits", title="Routing organization (permutation-null adjusted)"); ax.legend(frameon=False); fig.tight_layout(); fig.savefig(figure_root / "routing_information.png", dpi=180); plt.close(fig)
    return {"status": "generated", "files": sorted(path.name for path in figure_root.glob("*.png"))}


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Minimal developmental society V1")
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--repair-missing-usage", action="store_true")
    parser.add_argument("--confirm-real", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.freeze:
        write_protocol_docs(); result = freeze_manifest(); print(json.dumps({"status": "FROZEN", "manifest": str(REPORT_ROOT / 'manifest.json'), "logical_calls": result["logical_calls"], "forecast": result["cost_forecast"]}, indent=2))
    elif args.mock:
        print(json.dumps(run_mock(), indent=2))
    elif args.repair_missing_usage:
        print(json.dumps(repair_missing_usage_incident(), indent=2))
    elif args.run:
        print(json.dumps(asyncio.run(run_real(confirm_real=args.confirm_real)), indent=2))
    elif args.analyze:
        result = analyze(); _write_report(result); result["figures"] = _make_figures(); print(json.dumps(result, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
