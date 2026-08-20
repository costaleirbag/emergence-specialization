"""Controlled single-agent memory-representation × thinking calibration.

The runner is intentionally separate from the society experiment.  It uses the
same task, system prompt, parser, and teacher-correct exemplar semantics while
changing only memory serialization and the documented DeepSeek V4 thinking
toggle.  Raw events are append-only and query IDs include all factors plus the
replicate ID, so equal prompts are measured rather than deduplicated.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import random
import time
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from .agents import DEFAULT_SYSTEM_PROMPT, ExperimentalAgent, stable_hash
from .config import load_config
from .costs import estimate_usage_cost
from .environment import HiddenWorldEnvironment, task_prompt
from .experiment import make_backend
from .memory import MemoryPolicy
from .models import Experience, Task
from .parsing import ResponseParseError, parse_agent_output
from .probes import load_probe_set
from .retry import retry_delay

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "configs/research/memory_representation_thinking_v1.yaml"
PROTOCOL = "memory-representation-thinking-v1"
WORLDS = ("ALPHA", "BETA", "GAMMA", "DELTA")
REPRESENTATIONS = ("full_experience", "feedback_only")
REASONING_MODES = ("off", "high")


def _sha256_bytes(value: bytes) -> str: return hashlib.sha256(value).hexdigest()
def _sha256_file(path: Path) -> str: return _sha256_bytes(path.read_bytes())


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    os.replace(temp, path)


def load_spec(path: str | Path = DEFAULT_CONFIG) -> tuple[dict[str, Any], Any, Path]:
    config_path = Path(path).resolve(); spec = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(spec, dict): raise ValueError("memory representation config must be a mapping")
    base = load_config((ROOT / str(spec["base_config"])).resolve())
    return spec, base, config_path


def balanced_probe_tasks(environment: HiddenWorldEnvironment, *, probes_per_world: int = 14) -> list[Task]:
    """Deterministically choose exactly two inputs for each answer label/world."""
    if probes_per_world != 14: raise ValueError("this protocol requires exactly 14 probes/world")
    tasks: list[Task] = []
    for world in environment.worlds:
        by_label: dict[int, list[tuple[int, int]]] = {label: [] for label in range(7)}
        for x in range(environment.x_min, environment.x_max + 1):
            for y in range(environment.x_min, environment.x_max + 1):
                label = environment.answer_for(world, x, y)
                if len(by_label[label]) < 2: by_label[label].append((x, y))
        if any(len(values) != 2 for values in by_label.values()):
            raise ValueError(f"cannot construct balanced probe set for {world}: {by_label}")
        index = 0
        for label in range(7):
            for x, y in by_label[label]:
                tasks.append(Task(world=world, x=x, y=y, correct_answer=label, task_id=f"balanced-{world}-{index}")); index += 1
    return tasks


def _probe_map(tasks: list[Task]) -> dict[str, list[Task]]:
    grouped = {world: [] for world in WORLDS}
    for task in tasks: grouped[task.world].append(task)
    return grouped


def _exemplars(environment: HiddenWorldEnvironment, probes: dict[str, list[Task]], world: str, seed: int) -> list[Experience]:
    rng = random.Random(0xA11CE + seed * 1009 + sum(ord(c) for c in world) * 17)
    blocked = {(task.x, task.y) for task in probes[world]}; chosen: list[Experience] = []; seen: set[tuple[int, int]] = set()
    while len(chosen) < 8:
        pair = (rng.randint(environment.x_min, environment.x_max), rng.randint(environment.x_min, environment.x_max))
        if pair in blocked or pair in seen: continue
        seen.add(pair); answer = environment.answer_for(world, *pair)
        chosen.append(Experience(round_id=0, world=world, x=pair[0], y=pair[1], prediction=answer, confidence=1.0, correct_answer=answer, was_correct=True))
    return chosen


def _render_memory(memory: list[Experience], representation: str, *, corrupted: bool = False) -> list[dict[str, Any]]:
    if representation == "full_experience" and not corrupted: return [item.prompt_dict() for item in memory]
    # Feedback-only deliberately omits prediction, confidence, and was_correct.
    rendered = []
    for item in memory:
        answer = (item.correct_answer + 1) % 7 if corrupted else item.correct_answer
        rendered.append({"world": item.world, "x": item.x, "y": item.y, "correct_answer": answer})
    return rendered


def _prompt(task: Task, system_prompt: str, rendered_memory: list[dict[str, Any]]) -> tuple[str, str]:
    memory_json = json.dumps(rendered_memory, sort_keys=True, separators=(",", ":"))
    user = ("Your controlled feedback memory is below. It is the only source of past experience available for this task.\n"
            "CONTROLLED_MEMORY_JSON:\n" + memory_json + "\n\nCURRENT_TASK:\n" + task_prompt(task) +
            '\n\nReturn only a JSON object matching exactly this schema, with no Markdown:\n{"answer": <integer 0..6>, "confidence": <number 0..1>}')
    return user, stable_hash(system_prompt + "\n\n" + user)


def _probe_hash(tasks: list[Task]) -> str: return _sha256_bytes(json.dumps([asdict(task) for task in tasks], sort_keys=True, separators=(",", ":")).encode())


def expected_query_count(spec: dict[str, Any]) -> int:
    worlds, seeds, probes, reps = len(spec["worlds"]), int(spec["context_seeds"]), int(spec["probes_per_world"]), int(spec["replicates"])
    reasoning = len(spec["reasoning_modes"]); nonzero = len(spec["k_values"]) - 1
    per_reasoning = worlds * seeds * probes * reps + worlds * seeds * nonzero * probes * reps * len(spec["representations"])
    corrupted = worlds * seeds * probes * reps if bool(spec.get("include_truly_corrupted_feedback")) else 0
    return reasoning * (per_reasoning + corrupted)


def preflight(path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    spec, base, config_path = load_spec(path)
    if base.agent.backend != "deepseek_direct" or base.agent.model != "deepseek-v4-flash": raise ValueError("base must be DeepSeek Direct V4 Flash")
    if tuple(spec["reasoning_modes"]) != REASONING_MODES: raise ValueError("reasoning modes must be exactly off,high")
    if tuple(spec["representations"]) != REPRESENTATIONS: raise ValueError("representations must be full_experience,feedback_only")
    environment = HiddenWorldEnvironment(worlds=tuple(spec["worlds"]), x_min=base.environment.x_min, x_max=base.environment.x_max)
    tasks = balanced_probe_tasks(environment, probes_per_world=int(spec["probes_per_world"])); grouped = _probe_map(tasks)
    histogram = {world: {label: sum(task.correct_answer == label for task in grouped[world]) for label in range(7)} for world in spec["worlds"]}
    if any(set(counts.values()) != {2} for counts in histogram.values()): raise ValueError(f"balanced label invariant failed: {histogram}")
    contexts: list[dict[str, Any]] = []
    for world in spec["worlds"]:
        for seed in range(1, int(spec["context_seeds"]) + 1):
            pool = _exemplars(environment, grouped, world, seed)
            for k in spec["k_values"]:
                if int(k) == 0: contexts.append({"world": world, "seed": seed, "k": 0, "representation": "common_k0", "pool": []})
                else:
                    for rep in REPRESENTATIONS: contexts.append({"world": world, "seed": seed, "k": int(k), "representation": rep, "pool": [asdict(x) for x in pool[:int(k)]]})
            if spec.get("include_truly_corrupted_feedback"): contexts.append({"world": world, "seed": seed, "k": 8, "representation": "feedback_only", "mode": "truly_corrupted_feedback", "pool": [asdict(x) for x in pool]})
    probe_pairs = {(task.world, task.x, task.y) for task in tasks}
    if any((item["world"], item["x"], item["y"]) in probe_pairs for context in contexts for item in context["pool"]): raise ValueError("exemplar/probe overlap")
    return {"protocol": PROTOCOL, "config_path": str(config_path.relative_to(ROOT)), "config_hash": _sha256_file(config_path), "base_config": str(Path(base.source_path).resolve().relative_to(ROOT)), "base_config_hash": base.source_hash, "backend": base.agent.backend, "model": base.agent.model, "thinking_modes": list(spec["reasoning_modes"]), "thinking_max_tokens": int(spec.get("thinking_max_tokens", 2048)), "thinking_support": "documented DeepSeek V4 API toggle; same model", "worlds": list(spec["worlds"]), "context_seeds": int(spec["context_seeds"]), "k_values": list(spec["k_values"]), "representations": list(spec["representations"]), "probes_per_world": len(grouped[spec["worlds"][0]]), "probe_hash": _probe_hash(tasks), "probe_label_histogram": histogram, "contexts": len(contexts), "planned_logical_queries": expected_query_count(spec), "hard_cost_cap_usd": float(spec["hard_cost_cap_usd"]), "max_physical_attempts": int(spec["max_physical_attempts"]), "reasoning_traces_persisted": False, "k0_deduplicated": True, "old_corrupted_control_renamed": True}


async def run_real(path: str | Path = DEFAULT_CONFIG, *, confirm_real: bool = False) -> dict[str, Any]:
    if not confirm_real: raise SystemExit("real inference requires --confirm-real")
    spec, base, config_path = load_spec(path); audit = preflight(path)
    output = (ROOT / str(spec["output_dir"])).resolve(); output.mkdir(parents=True, exist_ok=True)
    manifest_path, events_path = output / "manifest.json", output / "events.jsonl"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {**audit, "created_at_utc": datetime.now(UTC).isoformat(), "status": "running", "observed_cost_usd": 0.0, "physical_attempts": 0}
    events = [json.loads(line) for line in events_path.read_text().splitlines() if line.strip()] if events_path.exists() else []
    def completion_uses_current_cap(event: dict[str, Any]) -> bool:
        if event.get("reasoning") != "high": return True
        return int(event.get("max_tokens", 0)) == int(spec.get("thinking_max_tokens", 2048))
    existing = {str(event["query_id"]): event for event in events if event.get("event") == "completion" and event.get("error") is None and completion_uses_current_cap(event)}
    environment = HiddenWorldEnvironment(worlds=tuple(spec["worlds"]), x_min=base.environment.x_min, x_max=base.environment.x_max)
    probes = balanced_probe_tasks(environment, probes_per_world=int(spec["probes_per_world"])); grouped = _probe_map(probes)
    probe_manifest_path = (ROOT / str(spec["probe_set_path"])).resolve()
    if not probe_manifest_path.exists():
        _write_json(probe_manifest_path, {"protocol": PROTOCOL, "probe_hash": _probe_hash(probes), "tasks": [asdict(task) for task in probes], "label_histogram": {world: {label: sum(task.correct_answer == label for task in grouped[world]) for label in range(7)} for world in spec["worlds"]}})
    else:
        stored = json.loads(probe_manifest_path.read_text(encoding="utf-8"))
        if stored.get("probe_hash") != _probe_hash(probes) or stored.get("tasks") != [asdict(task) for task in probes]:
            raise RuntimeError("existing balanced probe manifest does not match deterministic protocol")
    contexts: list[dict[str, Any]] = []
    for world in spec["worlds"]:
        for seed in range(1, int(spec["context_seeds"]) + 1):
            pool = _exemplars(environment, grouped, world, seed)
            for k in spec["k_values"]:
                if int(k) == 0: contexts.append({"mode": "correct_feedback", "world": world, "seed": seed, "k": 0, "representation": "common_k0", "memory": [], "truth_memory": []})
                else:
                    for rep in REPRESENTATIONS: contexts.append({"mode": "correct_feedback", "world": world, "seed": seed, "k": int(k), "representation": rep, "memory": _render_memory(pool[:int(k)], rep), "truth_memory": [asdict(x) for x in pool[:int(k)]]})
            if spec.get("include_truly_corrupted_feedback"): contexts.append({"mode": "truly_corrupted_feedback", "world": world, "seed": seed, "k": 8, "representation": "feedback_only", "memory": _render_memory(pool, "feedback_only", corrupted=True), "truth_memory": [asdict(x) for x in pool]})
    mode_pairs = [("correct_feedback", context) for context in contexts if context["mode"] == "correct_feedback"] + [("truly_corrupted_feedback", context) for context in contexts if context["mode"] == "truly_corrupted_feedback"]
    system_prompt = base.agent.system_prompt or DEFAULT_SYSTEM_PROMPT
    backend = make_backend(base)
    lock = asyncio.Lock(); sem = asyncio.Semaphore(int(spec["max_concurrency"]))
    def event_cost(event: dict[str, Any]) -> float:
        direct = event.get("observed_cost_usd")
        if isinstance(direct, (int, float)) and direct > 0: return float(direct)
        return float(estimate_usage_cost(event.get("token_usage"), input_per_million_tokens=base.cost.input_per_million_tokens, cached_input_per_million_tokens=base.cost.cached_input_per_million_tokens, output_per_million_tokens=base.cost.output_per_million_tokens) or 0.0)
    physical = len(events); cost = sum(event_cost(event) for event in events); max_attempts = int(spec["technical_retries"]) + 1
    async def one(reasoning: str, context: dict[str, Any], task: Task, replicate: int) -> None:
        nonlocal physical, cost
        query = {"reasoning": reasoning, "mode": context["mode"], "world": context["world"], "seed": context["seed"], "k": context["k"], "representation": context["representation"], "task": asdict(task), "replicate": replicate}
        query_id = stable_hash(json.dumps(query, sort_keys=True, separators=(",", ":")))
        if query_id in existing: return
        user_prompt, prompt_hash = _prompt(task, system_prompt, context["memory"])
        for attempt in range(max_attempts):
            async with lock:
                if physical >= int(spec["max_physical_attempts"]): raise RuntimeError("physical-attempt guard reached")
                if cost >= float(spec["hard_cost_cap_usd"]): raise RuntimeError("cost cap reached")
                physical += 1
            started = time.perf_counter()
            max_tokens = int(spec.get("thinking_max_tokens", 2048)) if reasoning != "off" else int(base.agent.max_tokens or 128)
            async with sem: response = await backend.complete(system_prompt=system_prompt, user_prompt=user_prompt, model=base.agent.model, model_parameters={"thinking": reasoning, "reasoning_effort": "high", "max_tokens": max_tokens})
            latency = response.latency_s or (time.perf_counter() - started); token_usage = response.token_usage; observed = float(response.observed_cost_usd or estimate_usage_cost(token_usage, input_per_million_tokens=base.cost.input_per_million_tokens, cached_input_per_million_tokens=base.cost.cached_input_per_million_tokens, output_per_million_tokens=base.cost.output_per_million_tokens) or 0.0)
            error = response.error; error_category = response.error_category; parsed = None; confidence = None; answer_in_domain = None; semantic = None
            if error is None:
                try:
                    parsed_response = parse_agent_output(response.raw_response or "")
                    parsed = parsed_response.answer; confidence = parsed_response.confidence; answer_in_domain = 0 <= parsed <= 6; semantic = None if answer_in_domain else "answer_out_of_domain"
                except ResponseParseError as exc: error = f"ResponseParseError: {exc}"; error_category = "parse_error"
            event = {"event": "completion", "protocol": PROTOCOL, "query_id": query_id, "attempt": attempt, "reasoning": reasoning, "max_tokens": max_tokens, "mode": context["mode"], "representation": context["representation"], "target_world": context["world"], "context_seed": context["seed"], "k": context["k"], "replicate_id": replicate, "probe": asdict(task), "context": {"world": context["world"], "context_seed": context["seed"], "k": context["k"], "representation": context["representation"], "mode": context["mode"], "rendered_memory": context["memory"], "truth_memory": context["truth_memory"]}, "rendered_memory": context["memory"], "raw_model_response": response.raw_response, "parsed_answer": parsed, "confidence": confidence, "correct": bool(parsed is not None and parsed == task.correct_answer), "answer_in_domain": answer_in_domain, "semantic_violation": semantic, "prompt_hash": prompt_hash, "system_prompt_hash": stable_hash(system_prompt), "latency_s": latency, "token_usage": token_usage, "observed_cost_usd": observed, "error": error, "error_category": error_category, "retryable": response.retryable, "provider_metadata": response.provider_metadata or {}, "reasoning_trace_persisted": False}
            async with lock:
                cost += observed
                with events_path.open("a", encoding="utf-8") as handle: handle.write(json.dumps(event, sort_keys=True, default=str) + "\n")
            if error is None and parsed is not None: existing[query_id] = event; return
            if attempt + 1 >= max_attempts or not response.retryable: return
            await asyncio.sleep(retry_delay(attempt, base_s=1.0, max_s=30.0, jitter_s=0.25, logical_id=query_id, retry_after_s=response.retry_after_s))
    tasks = []
    for reasoning in spec["reasoning_modes"]:
        for _mode, context in mode_pairs:
            for task in grouped[context["world"]]:
                for replicate in range(int(spec["replicates"])): tasks.append(one(str(reasoning), context, task, replicate))
    batch = int(spec["max_concurrency"]) * 4
    for index in range(0, len(tasks), batch):
        await asyncio.gather(*tasks[index:index + batch]); manifest.update({"status": "running", "physical_attempts": physical, "observed_cost_usd": cost, "completed_logical_queries": len(existing)}); _write_json(manifest_path, manifest)
    manifest.update({"status": "completed", "physical_attempts": physical, "observed_cost_usd": cost, "completed_logical_queries": len(existing), "finished_at_utc": datetime.now(UTC).isoformat()}); _write_json(manifest_path, manifest)
    close = getattr(backend, "close", None)
    if callable(close):
        result = close()
        if hasattr(result, "__await__"): await result
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Memory representation x thinking calibration")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG)); parser.add_argument("--preflight", action="store_true"); parser.add_argument("--run", action="store_true"); parser.add_argument("--confirm-real", action="store_true")
    args = parser.parse_args()
    if args.preflight or not args.run: print(json.dumps(preflight(args.config), indent=2, sort_keys=True))
    if args.run: print(json.dumps(asyncio.run(run_real(args.config, confirm_real=args.confirm_real)), indent=2, sort_keys=True))


if __name__ == "__main__": main()
