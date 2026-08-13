"""Theory V1.1 harness-clean discriminating replication.

This module is deliberately separate from the historical Theory V1 runners.  It
freezes a new, minimal instrument (neutral JSON schema, fresh seeds and separate
artifact roots) while reusing the frozen ecological constructors and social
semantics.  Importing the module is always offline; real inference requires the
explicit ``--confirm-real`` flag.
"""

from __future__ import annotations

import argparse
import asyncio
import collections
import hashlib
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
from typing import Any, Iterable, Sequence

from .credentials import CredentialStore
from .models import BackendResponse
from .providers import DeepSeekDirectBackend
from .observable_learner_calibration import parse_decisions
from .theory_v1.ecologies import AffineBooleanV1, V31Fresh

ROOT = Path(__file__).resolve().parents[2]
REPORT_ROOT = ROOT / "reports/theory-v1-1"
DATA_ROOT = ROOT / "data/auto-research/theory-v1-1"
STAGE_A_ROOT = REPORT_ROOT / "harness_validation"
EVENTS_PATH = DATA_ROOT / "stage_a_events.jsonl"
STATUS_PATH = DATA_ROOT / "stage_a_status.json"
MANIFEST_PATH = REPORT_ROOT / "stage_a_manifest.json"
PROTOCOL = "THEORY-V1.1-HARNESS-CLEAN"
MODEL = "deepseek-v4-flash"
THINKING = "off"
MAX_TOKENS = 32
HARD_CAP_USD = 4.00
MAX_ATTEMPTS = 2
CONCURRENCY = 32
N_NICHES = 4
PROBES_PER_NICHE = 8
STAGE_A_CONDITIONS = ("h0", "same_h4", "same_h8", "foreign_h8")
ECOLOGIES = ("V31_FRESH", "AFFINE_BOOLEAN_V1")
VALIDATION_SEEDS = {
    "V31_FRESH": (94101, 94102, 94103, 94104),
    "AFFINE_BOOLEAN_V1": (95101, 95102, 95103, 95104),
}
MICRO_SEEDS_V11 = {
    "V31_FRESH": (96101, 96102, 96103, 96104, 96105, 96106),
    "AFFINE_BOOLEAN_V1": (97101, 97102, 97103, 97104, 97105, 97106),
}
SOCIAL_SEEDS_V11 = {
    "V31_FRESH": (98101, 98102, 98103, 98104, 98105, 98106),
    "AFFINE_BOOLEAN_V1": (99101, 99102, 99103, 99104, 99105, 99106),
}
MACRO_CELLS_V11 = (
    {"cell_id": "C0", "k": 8, "beta": 0.0, "epsilon": 0.10, "q_share": 0.0},
    {"cell_id": "C1", "k": 8, "beta": 4.0, "epsilon": 0.10, "q_share": 0.0},
    {"cell_id": "C2", "k": 8, "beta": 8.0, "epsilon": 0.10, "q_share": 0.0},
    {"cell_id": "C3", "k": 8, "beta": 12.0, "epsilon": 0.10, "q_share": 0.0},
    {"cell_id": "C4", "k": 8, "beta": 20.0, "epsilon": 0.10, "q_share": 0.0},
    {"cell_id": "C5", "k": 8, "beta": 16.0, "epsilon": 0.55, "q_share": 0.0},
    {"cell_id": "C6", "k": 8, "beta": 12.0, "epsilon": 0.10, "q_share": 0.5},
    {"cell_id": "C7", "k": 8, "beta": 12.0, "epsilon": 0.10, "q_share": 1.0},
)
SYSTEM_PROMPT = (
    "You are a single-agent decision learner. Use resolved cases only as "
    "feedback-only memory. Return only the requested JSON object."
)
# Deliberately contains no complete valid three-bit vector.  This string is
# included verbatim in every V1.1 model-facing prompt.
CLEAN_OUTPUT_INSTRUCTION = (
    'Return only a JSON object with one key named "decisions". Its value must be '
    "an array containing exactly three binary integers. Do not include any other "
    "keys or text."
)
STATIC_INSTRUCTIONS = (SYSTEM_PROMPT, CLEAN_OUTPUT_INSTRUCTION)
RETRYABLE = {"parse_error", "empty_content", "transient_transport", "transport", "rate_limit", "server_error", "overloaded"}
INPUT_PRICE = 0.14
CACHED_INPUT_PRICE = 0.0028
OUTPUT_PRICE = 0.28
RESERVATION_USD = 0.0001


def now() -> str:
    return datetime.now(UTC).isoformat()


def stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def assert_no_concrete_answer_vectors(instructions: Iterable[str] = STATIC_INSTRUCTIONS) -> None:
    forbidden = {json.dumps(list(bits), separators=(",", ":")) for bits in itertools.product((0, 1), repeat=3)}
    for instruction in instructions:
        for vector in forbidden:
            if vector in instruction.replace(" ", ""):
                raise AssertionError(f"concrete answer vector leaked into static instruction: {vector}")


def _constructor(ecology: str) -> Any:
    if ecology == "V31_FRESH":
        return V31Fresh
    if ecology == "AFFINE_BOOLEAN_V1":
        return AffineBooleanV1
    raise ValueError(ecology)


def _support(ecology: str) -> list[tuple[int, ...]]:
    return list(itertools.product(range(4), repeat=3)) if ecology == "V31_FRESH" else list(itertools.product(range(2), repeat=6))


def _case(ecology: str, seed: int, niche: int, x: tuple[int, ...], role: str, index: int) -> dict[str, Any]:
    resolved = _constructor(ecology).resolved(seed, niche, x, role)
    return {"case_id": f"{ecology}:{seed}:{role}:{niche}:{index}:{''.join(map(str, x))}", "niche": niche, "x": list(x), "y": list(resolved.y), "template_id": int(resolved.template_id), "role": role, "seed": seed}


def _render(ecology: str, item: dict[str, Any]) -> str:
    resolved = _constructor(ecology).resolved(int(item["seed"]), int(item["niche"]), tuple(item["x"]), item.get("role", "training"))
    return _constructor(ecology).render(resolved)


def render_user(ecology: str, task: dict[str, Any], memory: Sequence[dict[str, Any]]) -> str:
    parts: list[str] = []
    if memory:
        parts.append("Prior resolved cases:\n" + "\n\n".join(f"{_render(ecology, item)}\nResolved decision: {json.dumps(item['y'], separators=(',', ':'))}" for item in memory))
    parts.append("CURRENT CASE:\n" + _render(ecology, task))
    parts.append(CLEAN_OUTPUT_INSTRUCTION)
    return "\n\n".join(parts)


def _evaluation_x(ecology: str, seed: int) -> list[tuple[int, ...]]:
    support = _support(ecology)
    rng = random.Random(seed * 1009 + 701)
    return sorted(rng.sample(support, PROBES_PER_NICHE))


def _history(ecology: str, seed: int, source: int, count: int, evaluation: set[tuple[int, ...]]) -> list[dict[str, Any]]:
    support = [x for x in _support(ecology) if x not in evaluation]
    rng = random.Random(seed * 1009 + source * 7919 + count * 31)
    rng.shuffle(support)
    return [_case(ecology, seed, source, x, "training", i) for i, x in enumerate(support[:count])]


def _novel_seed_audit() -> dict[str, Any]:
    targets = sorted({seed for values in VALIDATION_SEEDS.values() for seed in values} | {seed for values in MICRO_SEEDS_V11.values() for seed in values} | {seed for values in SOCIAL_SEEDS_V11.values() for seed in values})
    hits: dict[str, list[str]] = {str(seed): [] for seed in targets}
    # A targeted ripgrep audit avoids parsing giant historical event manifests
    # and, crucially, never treats a random hash substring as a seed collision.
    # The command is read-only and is also what the human audit can reproduce.
    for seed in targets:
        pattern = rf'"(seed|environment_seed|social_seed|micro_seed)"[[:space:]]*:[[:space:]]*"?{seed}"?([[:space:],}}]|$)'
        try:
            result = subprocess.run(
                ["rg", "-l", "-e", pattern, "reports", "data", "--glob", "*.json"],
                cwd=ROOT, capture_output=True, text=True, check=False, timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        hits[str(seed)] = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    collisions = {seed: paths for seed, paths in hits.items() if paths}
    if collisions:
        raise RuntimeError(f"V1.1 fresh-seed collision: {collisions}")
    return {"checked": targets, "collisions": collisions}


def build_stage_a_tasks() -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for ecology in ECOLOGIES:
        for seed in VALIDATION_SEEDS[ecology]:
            eval_x = _evaluation_x(ecology, seed)
            eval_set = set(eval_x)
            for condition in STAGE_A_CONDITIONS:
                for target in range(N_NICHES):
                    if condition == "h0":
                        memory: list[dict[str, Any]] = []
                    else:
                        source = target if condition.startswith("same") else (target + 1) % N_NICHES
                        # Generate one deterministic h=8 history and take its
                        # prefix for h=4.  This makes the nested-history
                        # comparison literal rather than merely equal in size.
                        full_history = _history(ecology, seed, source, 8, eval_set)
                        memory = full_history[:4] if condition == "same_h4" else full_history
                    for probe_index, x in enumerate(eval_x):
                        probe = _case(ecology, seed, target, x, "evaluation", probe_index)
                        task = {"protocol": PROTOCOL, "stage": "A", "ecology": ecology, "seed": seed, "condition": condition, "source": None if not memory else int(memory[0]["niche"]), "target": target, "probe_index": probe_index, "probe": probe, "memory": memory}
                        task["prompt_hash"] = stable_hash({"system": SYSTEM_PROMPT, "user": render_user(ecology, probe, memory)})
                        task["logical_id"] = stable_hash(task)
                        tasks.append(task)
    expected = len(ECOLOGIES) * 4 * 4 * N_NICHES * PROBES_PER_NICHE
    if len(tasks) != expected or len(tasks) > 2048:
        raise RuntimeError(f"Stage A count mismatch: {len(tasks)} != {expected}")
    return tasks


def build_stage_a_manifest() -> dict[str, Any]:
    assert_no_concrete_answer_vectors()
    novelty = _novel_seed_audit()
    tasks = build_stage_a_tasks()
    payload = {"protocol": PROTOCOL, "created_at_utc": now(), "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "provider": "DeepSeek Direct", "model": MODEL, "thinking": THINKING, "max_tokens": MAX_TOKENS, "hard_cap_usd": HARD_CAP_USD, "ecologies": ECOLOGIES, "validation_seeds": VALIDATION_SEEDS, "conditions": STAGE_A_CONDITIONS, "tasks": tasks, "logical_calls": len(tasks), "fresh_seed_audit": novelty, "static_instruction_hashes": {"system": stable_hash(SYSTEM_PROMPT), "output": stable_hash(CLEAN_OUTPUT_INSTRUCTION)}}
    payload["tasks_hash"] = stable_hash(tasks)
    payload["manifest_hash"] = stable_hash(payload)
    if MANIFEST_PATH.exists():
        existing = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        if existing.get("manifest_hash") != stable_hash({k: v for k, v in existing.items() if k != "manifest_hash"}):
            raise RuntimeError("existing V1.1 Stage A manifest hash invalid")
        if existing.get("tasks_hash") != payload["tasks_hash"]:
            raise RuntimeError("existing V1.1 Stage A manifest differs; refusing regeneration")
        return existing
    atomic_json(MANIFEST_PATH, payload)
    return payload


def _usage_cost(response: BackendResponse) -> float | None:
    from .costs import estimate_usage_cost
    if response.observed_cost_usd is not None:
        return float(response.observed_cost_usd)
    return estimate_usage_cost(response.token_usage, input_per_million_tokens=INPUT_PRICE, cached_input_per_million_tokens=CACHED_INPUT_PRICE, output_per_million_tokens=OUTPUT_PRICE)


class RequestGate:
    def __init__(self, limit: int = CONCURRENCY):
        self.sem = asyncio.Semaphore(limit)
        self.limit = limit
        self.active = 0
        self.max_active = 0
        self.completed = 0

    async def __aenter__(self):
        await self.sem.acquire()
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.active -= 1
        self.completed += 1
        self.sem.release()


async def _complete(backend: DeepSeekDirectBackend, task: dict[str, Any], gate: RequestGate, lock: asyncio.Lock, attempts: dict[str, int], spent: list[float], budget: dict[str, float]) -> dict[str, Any]:
    logical_id = task["logical_id"]
    # ``spent`` and ``reserved`` are shared only for accounting; scientific
    # task state is entirely contained in the frozen task record.
    for attempt in range(attempts.get(logical_id, 0), MAX_ATTEMPTS):
        async with gate:
            async with lock:
                if spent[0] + float(budget["reserved"]) + RESERVATION_USD > HARD_CAP_USD + 1e-12:
                    raise RuntimeError("V1.1 hard budget guard reached before physical attempt")
                budget["reserved"] = float(budget["reserved"]) + RESERVATION_USD
            response: BackendResponse
            try:
                response = await backend.complete(system_prompt=SYSTEM_PROMPT, user_prompt=render_user(task["ecology"], task["probe"], task["memory"]), model=MODEL, model_parameters={"thinking": THINKING, "max_tokens": MAX_TOKENS})
            except Exception as exc:
                category = "transient_transport"
                response = BackendResponse(raw_response=None, latency_s=0.0, error=f"provider exception: {type(exc).__name__}", error_category=category, retryable=True, token_usage=None, provider_metadata={})
            cost = _usage_cost(response)
            async with lock:
                budget["reserved"] = max(0.0, float(budget["reserved"]) - RESERVATION_USD)
                if cost is not None:
                    spent[0] += cost
                if spent[0] > HARD_CAP_USD + 1e-12:
                    raise RuntimeError("V1.1 hard budget cap exceeded")
        provider = response.provider_metadata or {}
        if provider and provider.get("model") not in (None, MODEL):
            raise RuntimeError(f"V1.1 model identity changed: {provider.get('model')!r}")
        decisions, parse_category = parse_decisions(response.raw_response)
        category = response.error_category or parse_category
        terminal = decisions is not None or category == "out_of_domain"
        event = {"protocol": PROTOCOL, "event": "completion", "logical_id": logical_id, "attempt": attempt, "task": task, "decisions": decisions, "expected": task["probe"]["y"], "correct": bool(decisions is not None and decisions == task["probe"]["y"]), "error": response.error or parse_category, "error_category": category, "terminal": terminal, "raw_model_response": response.raw_response, "latency_s": response.latency_s, "token_usage": response.token_usage, "provider_metadata": provider, "attempt_cost_usd": cost, "finished_at_utc": now()}
        async with lock:
            append_jsonl(EVENTS_PATH, event)
        if terminal:
            return event
        if category not in RETRYABLE:
            raise RuntimeError(f"non-retryable V1.1 response: {category}")
        attempts[logical_id] = attempt + 1
    raise RuntimeError(f"V1.1 retry exhaustion: {logical_id}")


async def run_stage_a(*, confirm_real: bool = False, concurrency: int = CONCURRENCY) -> dict[str, Any]:
    if not confirm_real:
        raise SystemExit("V1.1 paid execution requires --confirm-real")
    manifest = build_stage_a_manifest()
    existing = []
    if EVENTS_PATH.exists():
        existing = [json.loads(line) for line in EVENTS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    terminal = {event["logical_id"] for event in existing if event.get("terminal")}
    attempts = collections.Counter(event["logical_id"] for event in existing)
    tasks = [task for task in manifest["tasks"] if task["logical_id"] not in terminal]
    if not tasks and len(terminal) == manifest["logical_calls"]:
        result = stage_a_analysis(manifest)
        atomic_json(STATUS_PATH, {"protocol": PROTOCOL, "status": "completed", "logical_calls": len(terminal), "observed_cost_usd": sum(float(e.get("attempt_cost_usd") or 0) for e in existing)})
        return result
    forecast_result = forecast()
    if forecast_result["decision"] != "PROCEED":
        raise RuntimeError("V1.1 projected campaign cost with safety margin exceeds hard cap")
    key = CredentialStore().get(source="keychain")
    backend = DeepSeekDirectBackend(api_key=key, thinking=THINKING, max_tokens=MAX_TOKENS, max_connections=concurrency, max_keepalive_connections=concurrency)
    gate = RequestGate(concurrency); lock = asyncio.Lock(); spent = [sum(float(e.get("attempt_cost_usd") or 0) for e in existing)]
    budget = {"reserved": 0.0}
    try:
        results = await asyncio.gather(*[_complete(backend, task, gate, lock, attempts, spent, budget) for task in tasks])
        terminal.update(event["logical_id"] for event in results)
        all_events = [json.loads(line) for line in EVENTS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
        status = {"protocol": PROTOCOL, "status": "completed" if len(terminal) == manifest["logical_calls"] else "incomplete", "logical_calls": len(terminal), "expected_logical_calls": manifest["logical_calls"], "physical_attempts": len(all_events), "retries": sum(max(0, int(e.get("attempt", 0))) for e in all_events), "observed_cost_usd": sum(float(e.get("attempt_cost_usd") or 0) for e in all_events), "max_active_requests": gate.max_active, "global_request_limit": gate.limit, "finished_at_utc": now()}
        atomic_json(STATUS_PATH, status)
        if status["status"] != "completed":
            raise RuntimeError("V1.1 Stage A incomplete")
    finally:
        await backend.close()
    return stage_a_analysis(manifest)


def _valid_events() -> list[dict[str, Any]]:
    if not EVENTS_PATH.exists():
        return []
    return [json.loads(line) for line in EVENTS_PATH.read_text(encoding="utf-8").splitlines() if line.strip() and json.loads(line).get("terminal")]


def _accuracy(rows: Sequence[dict[str, Any]], *, bit: int | None = None) -> float:
    if not rows:
        return float("nan")
    if bit is None:
        return statistics.mean(int(row["correct"]) for row in rows)
    return statistics.mean(int(row["decisions"] is not None and row["decisions"][bit] == row["expected"][bit]) for row in rows)


def stage_a_analysis(manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    manifest = manifest or json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    rows = _valid_events()
    if len({row["logical_id"] for row in rows}) != manifest["logical_calls"]:
        raise RuntimeError("Stage A analysis requires complete unique terminal coverage")
    vectors = collections.Counter(tuple(row["decisions"]) for row in rows if row.get("decisions") is not None)
    total = sum(vectors.values())
    vector_rows = [{"vector": json.dumps(list(vector)), "count": count, "fraction": count / total if total else 0.0} for vector, count in sorted(vectors.items())]
    STAGE_A_ROOT.mkdir(parents=True, exist_ok=True)
    with (STAGE_A_ROOT / "response_vector_frequencies.csv").open("w", encoding="utf-8") as handle:
        handle.write("vector,count,fraction\n"); handle.writelines(f"{row['vector']},{row['count']},{row['fraction']}\n" for row in vector_rows)
    truth = collections.Counter(tuple(row["expected"]) for row in rows)
    with (STAGE_A_ROOT / "truth_vector_frequencies.csv").open("w", encoding="utf-8") as handle:
        handle.write("vector,count,fraction\n"); handle.writelines(f"{json.dumps(list(vector))},{count},{count/len(rows)}\n" for vector, count in sorted(truth.items()))
    units = []
    for ecology in ECOLOGIES:
        for seed in VALIDATION_SEEDS[ecology]:
            subset = [row for row in rows if row["task"]["ecology"] == ecology and int(row["task"]["seed"]) == seed]
            vals = {}
            for condition in STAGE_A_CONDITIONS:
                part = [row for row in subset if row["task"]["condition"] == condition]
                vals[condition] = {"joint": _accuracy(part), "bit": _accuracy(part, bit=0) if part else float("nan"), "bit1": _accuracy(part, bit=1) if part else float("nan"), "bit2": _accuracy(part, bit=2) if part else float("nan"), "n": len(part)}
            a0, same4, same8, foreign8 = vals["h0"]["joint"], vals["same_h4"]["joint"], vals["same_h8"]["joint"], vals["foreign_h8"]["joint"]
            units.append({"ecology": ecology, "seed": seed, "A0": a0, "A_same4": same4, "A_same8": same8, "A_foreign8": foreign8, "G_abs8": same8 - a0, "G_rel8": (same8 - a0) / (1 - a0) if a0 < 1 else 0.0, "bit_A0": vals["h0"]["bit"], "bit_A_same8": vals["same_h8"]["bit"], "conditions": vals})
    with (STAGE_A_ROOT / "local_plasticity.csv").open("w", encoding="utf-8") as handle:
        fields = ["ecology", "seed", "A0", "A_same4", "A_same8", "A_foreign8", "G_abs8", "G_rel8", "bit_A0", "bit_A_same8"]
        handle.write(",".join(fields) + "\n")
        for row in units: handle.write(",".join(str(row[f]) for f in fields) + "\n")
    pooled_a0 = statistics.mean(row["A0"] for row in units); pooled_same8 = statistics.mean(row["A_same8"] for row in units)
    max_vector, max_count = vectors.most_common(1)[0] if vectors else (None, 0)
    parse_failures = sum(1 for event in (json.loads(line) for line in EVENTS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()) if event.get("error_category") in {"parse_error", "empty_content"})
    model_ok = all((row.get("provider_metadata") or {}).get("model") in (None, MODEL) for row in rows)
    gates = {
        "HV1_anchor_collapse_removed": vectors.get((0, 1, 0), 0) / total < 0.50 if total else False,
        "HV2_no_single_output_mode_dominates": max_count / total < 0.70 if total else False,
        "HV3_useful_local_plasticity": pooled_same8 - pooled_a0 > 0 and statistics.mean(row["G_rel8"] for row in units) > 0,
        "HV4_same_history_not_worse": sum(row["A_same8"] > row["A0"] for row in units) >= 6,
        "HV5_technical_health": model_ok and parse_failures / max(1, len(rows)) <= 0.02,
    }
    analysis = {"protocol": PROTOCOL, "status": "PASS" if all(gates.values()) else "STOP", "logical_calls": len(rows), "predicted_vectors": vector_rows, "units": units, "pooled": {"A0": pooled_a0, "A_same4": statistics.mean(row["A_same4"] for row in units), "A_same8": pooled_same8, "A_foreign8": statistics.mean(row["A_foreign8"] for row in units), "G_abs8": pooled_same8 - pooled_a0, "G_rel8": statistics.mean(row["G_rel8"] for row in units), "p_010": vectors.get((0, 1, 0), 0) / total if total else 0.0, "modal_vector": list(max_vector) if max_vector is not None else None, "modal_fraction": max_count / total if total else 0.0}, "parse_failures": parse_failures, "model_ok": model_ok, "gates": gates}
    atomic_json(STAGE_A_ROOT / "harness_gate_results.json", analysis)
    return analysis


def forecast() -> dict[str, Any]:
    historical = []
    for path in (ROOT / "data/auto-research/theory-v1/micro_status.json", ROOT / "data/auto-research/theory-v1/macro/macro_status.json"):
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8")); calls = float(data.get("physical_attempts") or data.get("logical_calls") or 0); cost = float(data.get("observed_cost_usd") or 0)
            if calls and cost: historical.append(cost / calls)
    rate = max(historical) if historical else 0.00004
    counts = {"stage_a": len(ECOLOGIES) * 4 * 4 * N_NICHES * PROBES_PER_NICHE, "micro": 19584, "macro": 62976}
    total = sum(counts.values())
    result = {"per_attempt_rate_upper_observed": rate, "counts": counts, "expected_total_logical_calls": total, "projected_cost": total * rate, "projected_cost_with_50pct_margin": total * rate * 1.5, "hard_cap_usd": HARD_CAP_USD, "decision": "PROCEED" if total * rate * 1.5 <= HARD_CAP_USD else "STOP_FOR_REVIEW"}
    atomic_json(REPORT_ROOT / "cost_forecast.json", result)
    return result


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Theory V1.1 harness-clean replication")
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--forecast", action="store_true")
    parser.add_argument("--stage-a", action="store_true")
    parser.add_argument("--analyze-stage-a", action="store_true")
    parser.add_argument("--confirm-real", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.plan:
        manifest = build_stage_a_manifest(); print(json.dumps({"logical_calls": manifest["logical_calls"], "tasks_hash": manifest["tasks_hash"]}, indent=2))
    if args.forecast:
        print(json.dumps(forecast(), indent=2))
    if args.analyze_stage_a:
        print(json.dumps(stage_a_analysis(), indent=2))
    if args.stage_a:
        print(json.dumps(asyncio.run(run_stage_a(confirm_real=args.confirm_real)), indent=2))


if __name__ == "__main__":
    main()
