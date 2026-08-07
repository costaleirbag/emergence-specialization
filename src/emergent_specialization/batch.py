"""Plan multi-seed batches without executing providers.

The planner is intentionally a pure expansion tool. It prints reproducible
commands for a human or a later scheduler; it never calls the experiment
runner itself.
"""

from __future__ import annotations

import argparse
import json
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

from .config import RunConfig, load_config
from .probes import load_probe_set


@dataclass(frozen=True)
class PlannedRun:
    seed: int
    condition: str
    config: str
    rounds: int
    checkpoints: tuple[int, ...]
    probe_count: int
    interaction_calls: int
    probe_calls: int
    nominal_calls: int
    max_physical_calls: int
    output_dir: str
    command: str


def nominal_call_counts(config: RunConfig, probe_count: int) -> dict[str, int]:
    interactions = config.experiment.num_rounds * config.experiment.num_agents
    probes = len(config.experiment.checkpoints) * probe_count * config.experiment.num_agents
    nominal = interactions + probes
    return {
        "interaction_calls": interactions,
        "probe_calls": probes,
        "nominal_calls": nominal,
        "max_physical_calls": nominal * (config.experiment.technical_retries + 1),
    }


def _resolve_config(path: str, base: Path) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = (base / candidate).resolve()
        if not candidate.is_file():
            candidate = Path(path).expanduser().resolve()
    return candidate


def plan_batch(path: str | Path) -> list[PlannedRun]:
    batch_path = Path(path).expanduser().resolve()
    raw = yaml.safe_load(batch_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("batch config must be a YAML mapping")
    seeds = raw.get("seeds")
    config_paths = raw.get("configs")
    if not isinstance(seeds, list) or not seeds or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
        raise ValueError("batch seeds must be a non-empty list of integers")
    if not isinstance(config_paths, list) or not config_paths:
        raise ValueError("batch configs must be a non-empty list")
    output_root = Path(str(raw.get("output_dir", "data/runs"))).expanduser()
    if not output_root.is_absolute():
        # Commands are printed for execution from the repository root, so keep
        # relative output semantics consistent with the experiment CLI.
        output_root = (Path.cwd() / output_root).resolve()
    planned: list[PlannedRun] = []
    for config_value in config_paths:
        config_path = _resolve_config(str(config_value), batch_path.parent)
        base_config = load_config(config_path)
        probes, _ = load_probe_set(base_config.logging.probe_set_path)
        counts = nominal_call_counts(base_config, len(probes))
        condition = base_config.condition.memory_mode
        for seed in seeds:
            destination = output_root / f"{condition}-seed{seed}"
            command = " ".join(
                shlex.quote(part)
                for part in (
                    "uv", "run", "python", "-m", "emergent_specialization.experiment",
                    "--config", str(config_path), "--seed", str(seed), "--output-dir", str(output_root),
                )
            )
            planned.append(
                PlannedRun(
                    seed=seed,
                    condition=condition,
                    config=str(config_path),
                    rounds=base_config.experiment.num_rounds,
                    checkpoints=base_config.experiment.checkpoints,
                    probe_count=len(probes),
                    **counts,
                    output_dir=str(destination),
                    command=command,
                )
            )
    return planned


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Plan a multi-seed experiment batch (no execution)")
    parser.add_argument("--config", required=True, help="Batch YAML path")
    parser.add_argument("--plan", action="store_true", help="Print the dry plan")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--execute", action="store_true", help="Rejected: this command is planning-only")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.execute:
        parser.error("batch execution is intentionally not implemented; run a generated command explicitly")
    if not args.plan:
        parser.error("planning is the default safety boundary; pass --plan")
    rows = [asdict(row) for row in plan_batch(args.config)]
    if args.json:
        print(json.dumps(rows, indent=2, sort_keys=True))
        return
    print("BATCH PLAN (no model calls)")
    for row in rows:
        print(
            f"seed={row['seed']} condition={row['condition']} rounds={row['rounds']} "
            f"checkpoints={list(row['checkpoints'])} probes={row['probe_count']} "
            f"calls={row['nominal_calls']} (max={row['max_physical_calls']}) "
            f"output={row['output_dir']}"
        )
        print(f"  {row['command']}")


if __name__ == "__main__":
    main()
