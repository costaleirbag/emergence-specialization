"""Resumable DeepSeek Direct runner for the frozen Theory V1 MICRO stage.

The module is intentionally separate from the society runtime.  It only
executes the already-frozen 17 memory states x 4 targets x 8 probes design,
records one terminal scientific observation per logical context, and never
constructs a router or social memory.  ``--confirm-real`` is required by the
CLI so importing or preparing the manifest cannot call a provider.
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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from emergent_specialization.studies.calibration import observable_learner_v1 as learner
from emergent_specialization.providers.credentials import CredentialStore
from emergent_specialization.studies.ecology.ecological_information_v31 import EVAL_TEMPLATE_IDS, TRAIN_TEMPLATE_IDS, observable_o, render_observable
from emergent_specialization.core.models import BackendResponse
from emergent_specialization.providers import DeepSeekDirectBackend
from emergent_specialization.studies.theory.v1.ecologies import AffineBooleanV1, V31Fresh
from emergent_specialization.studies.theory.v1.micro_design import (
    ECOLOGIES,
    K_VALUES,
    MICRO_CALLS_PER_UNIT,
    MICRO_MEMORY_STATES,
    MICRO_SEEDS,
    N_NICHES,
    PROBES_PER_NICHE,
    balanced_memory,
    double_swaps,
    micro_manifest,
    single_swaps,
    stable_hash,
)

ROOT = Path(__file__).resolve().parents[5]
REPORT_ROOT = ROOT / "reports/theory-v1"
DATA_ROOT = ROOT / "data/auto-research/theory-v1"
PROTOCOL = "THEORY-V1"
MODEL = "deepseek-v4-flash"
THINKING = "off"
MAX_TOKENS = 32
MAX_ATTEMPTS = 2
HARD_CAP_USD = 8.00
RESERVATION_USD = 0.00050
INPUT_PRICE = 0.14
CACHED_INPUT_PRICE = 0.0028
OUTPUT_PRICE = 0.28
DEFAULT_CONCURRENCY = 8
RETRYABLE = {
    "parse_error", "empty_content", "transient_transport", "transport",
    "rate_limit", "server_error", "overloaded",
}
SYSTEM_PROMPT = (
    "You are a single-agent decision learner. Use resolved cases only as "
    "feedback-only memory. Return only the requested JSON object."
)
OUTPUT_INSTRUCTION = (
    'Return only a JSON object with one key named "decisions". Its value must be '
    "an array containing exactly three binary integers. Do not include any other "
    "keys or text."
)


def now() -> str:
    return datetime.now(UTC).isoformat()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _constructor(ecology: str) -> Any:
    if ecology == V31Fresh.name:
        return V31Fresh
    if ecology == AffineBooleanV1.name:
        return AffineBooleanV1
    raise ValueError(ecology)


def _support(ecology: str) -> list[tuple[int, ...]]:
    if ecology == V31Fresh.name:
        return list(itertools.product(range(4), repeat=3))
    return list(itertools.product(range(2), repeat=6))


def _slot_inputs(ecology: str, seed: int, k: int) -> list[tuple[int, ...]]:
    support = _support(ecology)
    # Inputs are tied to physical memory slots, so a swap changes the niche
    # assignment while preserving the observed case position.  This is the
    # exact local-composition intervention specified by the MICRO design.
    return [support[(seed * 17 + k * 31 + slot * 13) % len(support)] for slot in range(k)]


def _assignment_states(seed: int, k: int) -> list[tuple[str, list[int]]]:
    base = [item["niche"] for item in balanced_memory(seed, k)]
    states: list[tuple[str, list[int]]] = [("balanced", base)]
    for index, swap in enumerate(single_swaps(seed, k)):
        assignment = list(base)
        assignment[int(swap["slot"])] = int(swap["target"])
        states.append((f"single_{index:02d}", assignment))
    for index, pair in enumerate(double_swaps(seed, k)):
        assignment = list(base)
        for swap in pair:
            assignment[int(swap["slot"])] = int(swap["target"])
        states.append((f"double_{index:02d}", assignment))
    if len(states) != MICRO_MEMORY_STATES:
        raise AssertionError(f"memory state count {len(states)} != {MICRO_MEMORY_STATES}")
    return states


def _case(ecology: str, seed: int, niche: int, x: tuple[int, ...], *, role: str, index: int) -> dict[str, Any]:
    constructor = _constructor(ecology)
    resolved = constructor.resolved(seed, niche, x, role)
    return {
        "case_id": f"{ecology}:{seed}:{role}:{niche}:{index}:{''.join(map(str, x))}",
        "niche": niche,
        "x": list(x),
        "y": list(resolved.y),
        "template_id": int(resolved.template_id),
        "role": role,
    }


def _render_case(ecology: str, item: dict[str, Any]) -> str:
    constructor = _constructor(ecology)
    resolved = constructor.resolved(int(item.get("seed", 0)), int(item["niche"]), tuple(item["x"]), item["role"])
    # V31's renderer is the frozen semantic surface; the affine ecology's
    # renderer is neutral and does not expose policy parameters or niche IDs.
    return constructor.render(resolved)


def _probe_xs(ecology: str, seed: int, k: int, memory_xs: set[tuple[int, ...]], target: int) -> list[tuple[int, ...]]:
    candidates = [x for x in _support(ecology) if x not in memory_xs]
    rng = random.Random(seed * 1009 + k * 9176 + target * 7919)
    rng.shuffle(candidates)
    chosen = candidates[:PROBES_PER_NICHE]
    if len(chosen) != PROBES_PER_NICHE:
        raise RuntimeError(f"insufficient held-out probes for {ecology}/{seed}/k{k}")
    return sorted(chosen)


def _memory_for(ecology: str, seed: int, k: int, assignment: list[int]) -> list[dict[str, Any]]:
    inputs = _slot_inputs(ecology, seed, k)
    memory = []
    for slot, (niche, x) in enumerate(zip(assignment, inputs)):
        item = _case(ecology, seed, niche, x, role="memory", index=slot)
        item["slot"] = slot
        item["seed"] = seed
        memory.append(item)
    return memory


def build_tasks() -> list[dict[str, Any]]:
    """Build the complete frozen 26,112-context MICRO manifest."""
    tasks: list[dict[str, Any]] = []
    for ecology in ECOLOGIES:
        for seed in MICRO_SEEDS[ecology]:
            for k in K_VALUES:
                states = _assignment_states(seed, k)
                base_memory = _memory_for(ecology, seed, k, states[0][1])
                memory_xs = {tuple(item["x"]) for item in base_memory}
                for state_index, (state_name, assignment) in enumerate(states):
                    memory = _memory_for(ecology, seed, k, assignment)
                    for target in range(N_NICHES):
                        for probe_index, x in enumerate(_probe_xs(ecology, seed, k, memory_xs, target)):
                            probe = _case(ecology, seed, target, x, role="probe", index=probe_index)
                            task = {
                                "protocol": PROTOCOL,
                                "ecology": ecology,
                                "seed": seed,
                                "k": k,
                                "state_index": state_index,
                                "state": state_name,
                                "target": target,
                                "probe_index": probe_index,
                                "probe": probe,
                                "memory": memory,
                            }
                            task["prompt_hash"] = stable_hash({"system": SYSTEM_PROMPT, "user": render_user(task)})
                            task["logical_id"] = stable_hash(task)
                            tasks.append(task)
    expected = sum(len(MICRO_SEEDS[name]) for name in ECOLOGIES) * len(K_VALUES) * MICRO_CALLS_PER_UNIT
    if len(tasks) != expected:
        raise RuntimeError(f"Theory V1 MICRO task count mismatch {len(tasks)} != {expected}")
    return tasks


def render_user(task: dict[str, Any]) -> str:
    parts: list[str] = []
    memory = task.get("memory") or []
    if memory:
        lines = []
        for item in memory:
            lines.append(f"{_render_case(task['ecology'], item)}\nResolved decision: {json.dumps(item['y'], separators=(',', ':'))}")
        parts.append("Prior resolved cases:\n" + "\n\n".join(lines))
    parts.append("CURRENT CASE:\n" + _render_case(task["ecology"], task["probe"]))
    parts.append(OUTPUT_INSTRUCTION)
    return "\n\n".join(parts)


def freeze_manifest(*, git_head: str | None = None) -> dict[str, Any]:
    tasks = build_tasks()
    base = micro_manifest()
    manifest = {
        "protocol": PROTOCOL,
        "created_at_utc": now(),
        "git_head": git_head or subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "provider": "deepseek_direct",
        "model": MODEL,
        "thinking": THINKING,
        "max_tokens": MAX_TOKENS,
        "hard_cap_usd": HARD_CAP_USD,
        "max_attempts": MAX_ATTEMPTS,
        "system_prompt_hash": stable_hash(SYSTEM_PROMPT),
        "output_instruction_hash": stable_hash(OUTPUT_INSTRUCTION),
        "design": base,
        "logical_calls": len(tasks),
        "tasks": tasks,
    }
    manifest["tasks_hash"] = stable_hash(tasks)
    path = REPORT_ROOT / "micro_execution_manifest.json"
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        if old.get("tasks_hash") != manifest["tasks_hash"]:
            raise RuntimeError("existing Theory V1 MICRO manifest differs")
        return old
    atomic_json(path, manifest)
    return manifest


def _cost(response: BackendResponse) -> float | None:
    from emergent_specialization.core.costs import estimate_usage_cost
    return estimate_usage_cost(
        response.token_usage,
        input_per_million_tokens=INPUT_PRICE,
        cached_input_per_million_tokens=CACHED_INPUT_PRICE,
        output_per_million_tokens=OUTPUT_PRICE,
    )


def _budget_change(*, reserve: float = 0.0, release: float = 0.0, actual: float = 0.0) -> dict[str, Any]:
    path = DATA_ROOT / "campaign_budget.json"
    lock_path = path.with_suffix(".lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        budget = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {
            "protocol": PROTOCOL, "hard_cap_usd": HARD_CAP_USD, "spent_usd": 0.0, "reserved_usd": 0.0,
        }
        spent = float(budget.get("spent_usd", 0.0))
        reserved = float(budget.get("reserved_usd", 0.0))
        if reserved + 1e-12 < release or spent + reserved - release + reserve + actual > HARD_CAP_USD + 1e-12:
            raise RuntimeError("Theory V1 hard budget guard")
        budget.update(spent_usd=spent + actual, reserved_usd=reserved - release + reserve, updated_at_utc=now())
        atomic_json(path, budget)
        return budget


async def run_micro(*, confirm_real: bool = False, concurrency: int = DEFAULT_CONCURRENCY) -> dict[str, Any]:
    if not confirm_real:
        raise SystemExit("Theory V1 MICRO execution requires --confirm-real")
    if concurrency < 1 or concurrency > 32:
        raise ValueError("concurrency must be in [1,32]")
    manifest = json.loads((REPORT_ROOT / "micro_execution_manifest.json").read_text(encoding="utf-8"))
    if manifest.get("logical_calls") != 26112 or manifest.get("tasks_hash") != stable_hash(manifest["tasks"]):
        raise RuntimeError("Theory V1 MICRO manifest integrity failure")
    events_path = DATA_ROOT / "micro_events.jsonl"
    status_path = DATA_ROOT / "micro_status.json"
    existing = learner._load_events(events_path)
    done = {event["logical_id"] for event in existing if event.get("terminal")}
    attempts: collections.defaultdict[str, int] = collections.defaultdict(int)
    for event in existing:
        attempts[event["logical_id"]] = max(attempts[event["logical_id"]], int(event.get("attempt", 0)) + 1)
    status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {
        "protocol": PROTOCOL, "status": "initialized", "tasks_hash": manifest["tasks_hash"],
        "logical_calls": manifest["logical_calls"], "created_at_utc": now(),
    }
    if status.get("tasks_hash") != manifest["tasks_hash"]:
        raise RuntimeError("Theory V1 MICRO status/manifest mismatch")
    status.update(status="running", concurrency=concurrency, started_or_resumed_at_utc=now())
    atomic_json(status_path, status)
    key = CredentialStore().get(source="keychain")
    backend = DeepSeekDirectBackend(api_key=key, thinking=THINKING, max_tokens=MAX_TOKENS, max_connections=concurrency, max_keepalive_connections=concurrency)
    semaphore = asyncio.Semaphore(concurrency)
    total_cost = sum(float(event.get("attempt_cost_usd") or 0.0) for event in existing)
    retry_count = sum(int(event.get("attempt", 0)) for event in existing)
    tasks = [task for task in manifest["tasks"] if task["logical_id"] not in done]
    lock = asyncio.Lock()

    async def one(task: dict[str, Any]) -> None:
        nonlocal total_cost, retry_count
        logical_id = task["logical_id"]
        attempt = attempts.get(logical_id, 0)
        while attempt < MAX_ATTEMPTS:
            _budget_change(reserve=RESERVATION_USD)
            try:
                async with semaphore:
                    response = await backend.complete(
                        system_prompt=SYSTEM_PROMPT,
                        user_prompt=render_user(task),
                        model=MODEL,
                        model_parameters={"thinking": THINKING, "max_tokens": MAX_TOKENS},
                    )
            except Exception as exc:
                # A transport exception may be billable even when the provider
                # returned no usage block.  Journal a nonterminal technical
                # attempt and charge the conservative reservation before
                # retrying, rather than losing the physical attempt.
                _budget_change(release=RESERVATION_USD, actual=RESERVATION_USD)
                event = {
                    "protocol": PROTOCOL, "logical_id": logical_id,
                    "attempt": attempt, "task": task, "decisions": None,
                    "expected": task["probe"]["y"], "correct": False,
                    "error": f"provider exception: {type(exc).__name__}",
                    "error_category": "transient_transport", "terminal": False,
                    "raw_model_response": None, "latency_s": None,
                    "token_usage": None, "provider_metadata": {},
                    "attempt_cost_usd": RESERVATION_USD,
                    "cost_source": "conservative_upper_bound_missing_usage",
                    "finished_at_utc": now(),
                }
                async with lock:
                    append_jsonl(events_path, event)
                    total_cost += RESERVATION_USD
                    retry_count += int(attempt)
                attempt += 1
                continue
            cost = _cost(response)
            if cost is None:
                # The completion exists but cannot be reconciled to provider
                # usage.  Preserve it as a technical non-observation and use a
                # conservative billable-attempt bound; the next attempt is the
                # only one eligible to become the scientific observation.
                _budget_change(release=RESERVATION_USD, actual=RESERVATION_USD)
                provider = response.provider_metadata or {}
                event = {
                    "protocol": PROTOCOL, "logical_id": logical_id,
                    "attempt": attempt, "task": task, "decisions": None,
                    "expected": task["probe"]["y"], "correct": False,
                    "error": response.error or "provider usage/cost unavailable",
                    "error_category": response.error_category or "usage_unavailable",
                    "terminal": False, "raw_model_response": response.raw_response,
                    "latency_s": response.latency_s, "token_usage": response.token_usage,
                    "provider_metadata": provider, "attempt_cost_usd": RESERVATION_USD,
                    "cost_source": "conservative_upper_bound_missing_usage",
                    "finished_at_utc": now(),
                }
                async with lock:
                    append_jsonl(events_path, event)
                    total_cost += RESERVATION_USD
                    retry_count += int(attempt)
                attempt += 1
                continue
            _budget_change(release=RESERVATION_USD, actual=cost)
            decisions, parse_category = learner.parse_decisions(response.raw_response)
            provider = response.provider_metadata or {}
            if provider.get("model") != MODEL:
                raise RuntimeError(f"Theory V1 model mismatch: {provider.get('model')!r}")
            category = response.error_category or parse_category
            error = response.error or parse_category
            terminal = category == "out_of_domain" or (error is None and decisions is not None)
            event = {
                "protocol": PROTOCOL, "logical_id": logical_id, "attempt": attempt,
                "task": task, "decisions": decisions, "expected": task["probe"]["y"],
                "correct": decisions == task["probe"]["y"] if decisions is not None else False,
                "error": error, "error_category": category, "terminal": terminal,
                "raw_model_response": response.raw_response, "latency_s": response.latency_s,
                "token_usage": response.token_usage, "provider_metadata": provider,
                "attempt_cost_usd": cost, "finished_at_utc": now(),
            }
            async with lock:
                append_jsonl(events_path, event)
                total_cost += cost
                retry_count += int(attempt)
            if terminal:
                return
            if not response.retryable or category not in RETRYABLE:
                raise RuntimeError(f"non-retryable Theory V1 MICRO response: {category}")
            attempt += 1
        raise RuntimeError(f"Theory V1 MICRO retry exhaustion for {logical_id}")

    try:
        # Tasks are deterministic and independent; completion order cannot
        # change any prompt or scientific state.  The journal is the source of
        # truth for resume and exact logical coverage.
        for offset in range(0, len(tasks), concurrency * 4):
            batch = tasks[offset:offset + concurrency * 4]
            await asyncio.gather(*(one(task) for task in batch))
            if offset % (concurrency * 40) == 0:
                status.update(completed_logical=len(done) + min(offset + len(batch), len(tasks)), observed_cost_usd=total_cost, physical_attempts=len(existing) + offset + len(batch), retries=retry_count)
                atomic_json(status_path, status)
        final_events = learner._load_events(events_path)
        final_done = {event["logical_id"] for event in final_events if event.get("terminal")}
        if len(final_done) != manifest["logical_calls"]:
            raise RuntimeError(f"Theory V1 MICRO coverage {len(final_done)}/{manifest['logical_calls']}")
        status.update(status="completed", completed_logical=len(final_done), physical_attempts=len(final_events), retries=sum(int(event.get("attempt", 0)) for event in final_events), observed_cost_usd=sum(float(event.get("attempt_cost_usd") or 0.0) for event in final_events), finished_at_utc=now())
    except Exception as exc:
        final_events = learner._load_events(events_path)
        status.update(status="incomplete", failure=f"{type(exc).__name__}: {exc}", completed_logical=len({event["logical_id"] for event in final_events if event.get("terminal")}), physical_attempts=len(final_events), retries=sum(int(event.get("attempt", 0)) for event in final_events), observed_cost_usd=sum(float(event.get("attempt_cost_usd") or 0.0) for event in final_events), finished_at_utc=now())
    finally:
        await backend.close()
        atomic_json(status_path, status)
    return status


def micro_health() -> dict[str, Any]:
    manifest = json.loads((REPORT_ROOT / "micro_execution_manifest.json").read_text(encoding="utf-8"))
    events = learner._load_events(DATA_ROOT / "micro_events.jsonl")
    terminal = {event["logical_id"] for event in events if event.get("terminal")}
    errors = collections.Counter(event.get("error_category") for event in events if event.get("error_category"))
    models = sorted({model for event in events for model in [(event.get("provider_metadata") or {}).get("model")] if model})
    cost = sum(float(event.get("attempt_cost_usd") or 0.0) for event in events)
    return {
        "protocol": PROTOCOL, "logical_expected": manifest["logical_calls"],
        "logical_terminal": len(terminal), "physical_attempts": len(events),
        "technical_retries": sum(int(event.get("attempt", 0)) for event in events),
        "error_categories": dict(errors), "coverage": len(terminal) / manifest["logical_calls"],
        "models": models, "observed_cost_usd": cost,
        "usage_coverage": sum(bool(event.get("token_usage")) for event in events) / len(events) if events else 0.0,
        "classification": "CLEAN" if len(terminal) == manifest["logical_calls"] and not any(int(event.get("attempt", 0)) for event in events) else ("COMPLETE_WITH_RETRIES" if len(terminal) == manifest["logical_calls"] else "INCOMPLETE"),
    }


def main(argv: list[str] | None = None) -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Theory V1 frozen MICRO runner")
    parser.add_argument("action", choices=("freeze", "run", "health"))
    parser.add_argument("--confirm-real", action="store_true")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    args = parser.parse_args(argv)
    if args.action == "freeze":
        result = freeze_manifest()
        print(json.dumps({"manifest": str(REPORT_ROOT / "micro_execution_manifest.json"), "logical_calls": result["logical_calls"], "tasks_hash": result["tasks_hash"]}, indent=2))
    elif args.action == "run":
        print(json.dumps(asyncio.run(run_micro(confirm_real=args.confirm_real, concurrency=args.concurrency)), indent=2, sort_keys=True))
    else:
        print(json.dumps(micro_health(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
