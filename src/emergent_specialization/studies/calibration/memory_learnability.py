"""Single-agent DeepSeek calibration for controlled memory learnability.

This is deliberately not part of the society dynamics.  It uses the frozen
agent/system/task rendering and parser, but has no router, no adaptive feedback
and no multi-agent state.  All query identities include replicate IDs so equal
prompts are intentionally measured three times rather than deduplicated.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import random
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

import yaml

from emergent_specialization.core.agents import ExperimentalAgent, DEFAULT_SYSTEM_PROMPT, stable_hash
from emergent_specialization.core.config import load_config
from emergent_specialization.core.costs import estimate_usage_cost
from emergent_specialization.core.environment import HiddenWorldEnvironment
from emergent_specialization.runtime.experiment import make_backend
from emergent_specialization.core.memory import MemoryPolicy
from emergent_specialization.core.models import Experience, Task
from emergent_specialization.core.parsing import ResponseParseError, parse_agent_output
from emergent_specialization.core.probes import load_probe_set
from emergent_specialization.core.retry import retry_delay


ROOT = Path(__file__).resolve().parents[4]
CONFIG_PATH = ROOT / "configs/research/memory_learnability_v1.yaml"
PROTOCOL = "memory-learnability-v1"
MODES = ("same_world", "corrupted_k8", "unrelated_k8", "mixed_k8")
WORLD_MAP = {"ALPHA": "BETA", "BETA": "GAMMA", "GAMMA": "DELTA", "DELTA": "ALPHA"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_spec(path: str | Path = CONFIG_PATH) -> tuple[dict[str, Any], Any, Path]:
    path = Path(path).resolve()
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(spec, dict):
        raise ValueError("memory learnability config must be a mapping")
    base_path = (ROOT / str(spec["base_config"])).resolve()
    base = load_config(base_path)
    return spec, base, path


def _probe_map(probe_path: Path) -> tuple[dict[str, list[Task]], str]:
    tasks, probe_hash = load_probe_set(probe_path)
    grouped: dict[str, list[Task]] = {world: [] for world in ("ALPHA", "BETA", "GAMMA", "DELTA")}
    for task in tasks:
        grouped[task.world].append(task)
    return grouped, probe_hash


def generate_exemplars(
    environment: HiddenWorldEnvironment,
    probe_map: dict[str, list[Task]],
    *,
    world: str,
    k: int,
    seed: int,
    corrupted: bool = False,
) -> list[Experience]:
    """Generate deterministic teacher-correct examples disjoint from probes."""
    rng = random.Random(0x5EED + seed * 1009 + sum(ord(c) for c in world) * 17)
    blocked = {(task.x, task.y) for task in probe_map.get(world, [])}
    chosen: list[Experience] = []
    seen: set[tuple[int, int]] = set()
    while len(chosen) < k:
        pair = (rng.randint(environment.x_min, environment.x_max), rng.randint(environment.x_min, environment.x_max))
        if pair in blocked or pair in seen:
            continue
        seen.add(pair)
        true_answer = environment.answer_for(world, *pair)
        prediction = (true_answer + 1) % 7 if corrupted else true_answer
        chosen.append(Experience(
            round_id=0,
            world=world,
            x=pair[0],
            y=pair[1],
            prediction=prediction,
            confidence=1.0,
            correct_answer=true_answer,
            was_correct=not corrupted,
        ))
    return chosen


def build_contexts(spec: dict[str, Any], base: Any, probe_map: dict[str, list[Task]]) -> list[dict[str, Any]]:
    environment = HiddenWorldEnvironment(worlds=tuple(spec["worlds"]), x_min=base.environment.x_min, x_max=base.environment.x_max)
    contexts: list[dict[str, Any]] = []
    n_seeds = int(spec["context_seeds"])
    for world in spec["worlds"]:
        for seed in range(n_seeds):
            for k in spec["k_values"]:
                examples = generate_exemplars(environment, probe_map, world=world, k=int(k), seed=seed)
                contexts.append({"mode": "same_world", "target_world": world, "context_seed": seed, "k": int(k), "memory": [asdict(item) for item in examples]})
            same = generate_exemplars(environment, probe_map, world=world, k=8, seed=seed)
            corrupted = generate_exemplars(environment, probe_map, world=world, k=8, seed=seed, corrupted=True)
            unrelated_world = WORLD_MAP[world]
            unrelated = generate_exemplars(environment, probe_map, world=unrelated_world, k=8, seed=seed)
            mixed: list[Experience] = []
            for source_world in spec["worlds"]:
                mixed.extend(generate_exemplars(environment, probe_map, world=source_world, k=2, seed=seed))
            contexts.extend([
                {"mode": "corrupted_k8", "target_world": world, "context_seed": seed, "k": 8, "memory": [asdict(item) for item in corrupted], "control_of": "same_world"},
                {"mode": "unrelated_k8", "target_world": world, "context_seed": seed, "k": 8, "memory": [asdict(item) for item in unrelated], "source_world": unrelated_world},
                {"mode": "mixed_k8", "target_world": world, "context_seed": seed, "k": 8, "memory": [asdict(item) for item in mixed], "composition": {source: 2 for source in spec["worlds"]}},
            ])
    return contexts


def expected_query_count(spec: dict[str, Any]) -> int:
    worlds = len(spec["worlds"]); seeds = int(spec["context_seeds"]); reps = int(spec["replicates"]); probes = int(spec["probes_per_world"])
    primary = worlds * len(spec["k_values"]) * seeds * probes * reps
    controls = worlds * 3 * seeds * probes * reps
    return primary + controls


def preflight(path: str | Path = CONFIG_PATH) -> dict[str, Any]:
    spec, base, config_path = load_spec(path)
    probe_map, probe_hash = _probe_map((ROOT / spec["probe_set_path"]).resolve())
    if base.agent.backend != "deepseek_direct" or base.agent.model != "deepseek-v4-flash" or base.agent.thinking != "off":
        raise ValueError("base configuration is not the frozen DeepSeek Direct v2 environment")
    if tuple(spec["k_values"]) != (0, 1, 2, 4, 8):
        raise ValueError("k values must be exactly 0,1,2,4,8")
    contexts = build_contexts(spec, base, probe_map)
    for context in contexts:
        memory = context["memory"]
        target = context["target_world"]
        if context["mode"] == "unrelated_k8" and any(item["world"] == target for item in memory):
            raise ValueError("unrelated context contains target-world memory")
        if context["mode"] == "mixed_k8" and {world: sum(item["world"] == world for item in memory) for world in spec["worlds"]} != {world: 2 for world in spec["worlds"]}:
            raise ValueError("mixed context is not exactly 2 examples per world")
        if context["mode"] == "corrupted_k8":
            if any(item["prediction"] == item["correct_answer"] for item in memory):
                raise ValueError("corrupted labels contain a correct label")
        probe_pairs = {
            (task.world, task.x, task.y)
            for tasks in probe_map.values()
            for task in tasks
        }
        if any((item["world"], item["x"], item["y"]) in probe_pairs for item in memory):
            raise ValueError("exemplar/probe overlap")
    planned = expected_query_count(spec)
    return {
        "protocol": PROTOCOL,
        "config_path": str(config_path.relative_to(ROOT)),
        "config_hash": _sha256(config_path),
        "base_config": str(Path(base.source_path).resolve().relative_to(ROOT)),
        "base_config_hash": base.source_hash,
        "model": base.agent.model,
        "backend": base.agent.backend,
        "thinking": base.agent.thinking,
        "worlds": list(spec["worlds"]),
        "k_values": list(spec["k_values"]),
        "context_seeds": int(spec["context_seeds"]),
        "probes_per_world": int(spec["probes_per_world"]),
        "replicates": int(spec["replicates"]),
        "planned_logical_queries": planned,
        "max_physical_attempts": int(spec["max_physical_attempts"]),
        "hard_cost_cap_usd": float(spec["hard_cost_cap_usd"]),
        "probe_set_hash": probe_hash,
        "contexts": len(contexts),
        "probe_updates_memory": False,
        "hidden_rule_leakage": False,
    }


def _query_id(context: dict[str, Any], probe: Task, replicate: int) -> str:
    payload = {"context": context, "probe": asdict(probe), "replicate": replicate}
    return stable_hash(json.dumps(payload, sort_keys=True, separators=(",", ":")))


async def run_real(path: str | Path = CONFIG_PATH, *, confirm_real: bool = False) -> dict[str, Any]:
    if not confirm_real:
        raise SystemExit("memory learnability real inference requires --confirm-real")
    spec, base, config_path = load_spec(path)
    audit = preflight(path)
    output = (ROOT / spec["output_dir"]).resolve(); output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "manifest.json"; events_path = output / "events.jsonl"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {
        **audit, "created_at_utc": datetime.now(UTC).isoformat(), "status": "running", "observed_cost_usd": 0.0, "physical_attempts": 0,
    }
    existing: dict[str, dict[str, Any]] = {}
    if events_path.exists():
        for line in events_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                event = json.loads(line)
                if event.get("event") == "completion" and event.get("error") is None:
                    existing[str(event["query_id"])] = event
    probe_map, probe_hash = _probe_map((ROOT / spec["probe_set_path"]).resolve())
    contexts = build_contexts(spec, base, probe_map)
    backend = make_backend(base)
    agent = ExperimentalAgent("calibration_agent")
    policy = MemoryPolicy("recent_k", 8)
    system_prompt = base.agent.system_prompt or DEFAULT_SYSTEM_PROMPT
    max_attempts = int(spec["technical_retries"]) + 1
    lock = asyncio.Lock(); physical = sum(1 for _ in events_path.read_text().splitlines()) if events_path.exists() else 0
    observed_cost = float(manifest.get("observed_cost_usd", 0.0))
    sem = asyncio.Semaphore(int(spec["max_concurrency"]))
    manifest["status"] = "running"; _json(manifest_path, manifest)

    async def one(context: dict[str, Any], probe: Task, replicate: int) -> None:
        nonlocal physical, observed_cost
        query_id = _query_id(context, probe, replicate)
        if query_id in existing:
            return
        memory = tuple(Experience(**item) for item in context["memory"])
        prompt, inserted = agent.prompt_parts(probe, policy, memory_snapshot=memory)
        prompt_hash = stable_hash(system_prompt + "\n\n" + prompt)
        for attempt in range(max_attempts):
            async with lock:
                if physical >= int(spec["max_physical_attempts"]):
                    raise RuntimeError("memory calibration physical-attempt guard reached")
                if observed_cost >= float(spec["hard_cost_cap_usd"]):
                    raise RuntimeError("memory calibration cost cap reached")
                physical += 1
            started = time.perf_counter()
            async with sem:
                response = await backend.complete(system_prompt=system_prompt, user_prompt=prompt, model=base.agent.model, model_parameters={"thinking": "off", "max_tokens": base.agent.max_tokens or 128})
            latency = response.latency_s or (time.perf_counter() - started)
            usage_cost = estimate_usage_cost(response.token_usage, input_per_million_tokens=base.cost.input_per_million_tokens, cached_input_per_million_tokens=base.cost.cached_input_per_million_tokens, output_per_million_tokens=base.cost.output_per_million_tokens)
            async with lock:
                observed_cost += float(usage_cost or 0.0)
            parsed_answer = confidence = None; answer_in_domain = semantic_violation = None; error = response.error; category = response.error_category; retryable = response.retryable
            if error is None and response.raw_response is not None:
                try:
                    parsed = parse_agent_output(response.raw_response); parsed_answer, confidence = parsed.answer, parsed.confidence; answer_in_domain, semantic_violation = parsed.answer_in_domain, parsed.semantic_violation
                except ResponseParseError as exc:
                    error = f"ResponseParseError: {exc}"; category = "parse_error"; retryable = True
            elif error is None:
                error = "empty response"; category = "empty_content"; retryable = True
            event = {
                "event": "completion", "query_id": query_id, "attempt": attempt, "protocol": PROTOCOL,
                "context_id": stable_hash(json.dumps(context, sort_keys=True, separators=(",", ":"))), "context": context,
                "target_world": context["target_world"], "mode": context["mode"], "context_seed": context["context_seed"], "k": context["k"],
                "probe": asdict(probe), "replicate_id": replicate, "prompt_hash": prompt_hash, "system_prompt_hash": stable_hash(system_prompt),
                "memory_inserted": inserted, "raw_model_response": response.raw_response, "parsed_answer": parsed_answer, "confidence": confidence,
                "answer_in_domain": answer_in_domain, "semantic_violation": semantic_violation, "correct": parsed_answer == probe.correct_answer if parsed_answer is not None else False,
                "latency_s": latency, "token_usage": response.token_usage, "observed_cost_usd": usage_cost, "error": error, "error_category": category,
                "retryable": retryable, "http_status": response.http_status, "provider_metadata": response.provider_metadata,
            }
            with events_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, sort_keys=True, default=str) + "\n")
            if error is None:
                existing[query_id] = event; return
            if not retryable or attempt + 1 >= max_attempts:
                return
            delay = retry_delay(attempt, base_s=1.0, max_s=30.0, jitter_s=0.25, logical_id=query_id, retry_after_s=response.retry_after_s)
            if delay > 0: await asyncio.sleep(delay)

    try:
        tasks = []
        for context in contexts:
            for probe in probe_map[context["target_world"]]:
                for replicate in range(int(spec["replicates"])):
                    tasks.append(one(context, probe, replicate))
        # Batches keep progress and cost accounting bounded while preserving
        # exact replicate identities and avoiding a giant task list in memory.
        batch_size = int(spec["max_concurrency"]) * 4
        for start in range(0, len(tasks), batch_size):
            await asyncio.gather(*tasks[start : start + batch_size])
            manifest.update({"physical_attempts": physical, "observed_cost_usd": observed_cost, "completed_logical_queries": len(existing)})
            _json(manifest_path, manifest)
    finally:
        close = getattr(backend, "close", None)
        if callable(close):
            await close()
    expected = audit["planned_logical_queries"]
    manifest.update({"status": "completed" if len(existing) == expected else "incomplete", "physical_attempts": physical, "observed_cost_usd": observed_cost, "completed_logical_queries": len(existing), "finished_at_utc": datetime.now(UTC).isoformat()})
    _json(manifest_path, manifest)
    return manifest


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Offline preflight or real single-agent memory learnability calibration")
    mode = parser.add_mutually_exclusive_group(required=True); mode.add_argument("--preflight", action="store_true"); mode.add_argument("--plan", action="store_true"); mode.add_argument("--run", action="store_true")
    parser.add_argument("--config", default=str(CONFIG_PATH)); parser.add_argument("--confirm-real", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    audit = preflight(args.config)
    if args.preflight or args.plan:
        print(json.dumps(audit, indent=2, sort_keys=True)); return
    print(json.dumps(asyncio.run(run_real(args.config, confirm_real=args.confirm_real)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
