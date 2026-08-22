"""Generation, loading, and integrity verification for the fixed probe set."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Iterable

from emergent_specialization.core.environment import HiddenWorldEnvironment
from emergent_specialization.core.models import Task


PROBE_GENERATION_SEED = 20260806


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_json(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def generate_probe_payload(
    environment: HiddenWorldEnvironment,
    *,
    seed: int = PROBE_GENERATION_SEED,
    per_world: int = 10,
) -> dict[str, object]:
    rng = random.Random(seed)
    tasks: list[dict[str, object]] = []
    for world in environment.worlds:
        seen: set[tuple[int, int]] = set()
        while len(seen) < per_world:
            pair = (rng.randint(environment.x_min, environment.x_max), rng.randint(environment.x_min, environment.x_max))
            if pair in seen:
                continue
            seen.add(pair)
            task = environment.make_task(world, *pair, task_id=f"probe-{world}-{len(seen) - 1}")
            tasks.append(task.experimenter_dict())
    body = {
        "format": "emergent-specialization-probe-set-v1",
        "generation_seed": seed,
        "worlds": list(environment.worlds),
        "per_world": per_world,
        "tasks": tasks,
    }
    return {**body, "content_sha256": sha256_json(body)}


def write_probe_set(path: str | Path, payload: dict[str, object]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_probe_set(path: str | Path) -> tuple[list[Task], str]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("probe set must be a JSON object")
    received_hash = payload.pop("content_sha256", None)
    expected_hash = sha256_json(payload)
    if received_hash != expected_hash:
        raise ValueError("probe set hash does not match its content")
    raw_tasks = payload.get("tasks")
    if not isinstance(raw_tasks, list):
        raise ValueError("probe set tasks must be a list")
    tasks = [Task(**item) for item in raw_tasks]
    worlds = payload.get("worlds")
    per_world = payload.get("per_world")
    if not isinstance(worlds, list) or not isinstance(per_world, int):
        raise ValueError("probe set metadata is invalid")
    if len(tasks) != len(worlds) * per_world:
        raise ValueError("probe set size does not match worlds × per_world")
    if {task.world for task in tasks} != set(worlds):
        raise ValueError("probe set world labels do not match metadata")
    return tasks, expected_hash


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate the fixed hidden-world probe set.")
    parser.add_argument("--output", default="data/probe_set.json")
    parser.add_argument("--seed", type=int, default=PROBE_GENERATION_SEED)
    parser.add_argument("--per-world", type=int, default=10)
    args = parser.parse_args(list(argv) if argv is not None else None)
    payload = generate_probe_payload(HiddenWorldEnvironment(), seed=args.seed, per_world=args.per_world)
    write_probe_set(args.output, payload)
    print(f"Wrote {len(payload['tasks'])} fixed probes to {args.output}")
    print(f"content_sha256={payload['content_sha256']}")


if __name__ == "__main__":
    main()
