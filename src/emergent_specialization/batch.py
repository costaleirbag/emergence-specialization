"""Plan multi-seed batches without executing providers.

The planner is intentionally a pure expansion tool. It prints reproducible
commands for a human or a later scheduler; it never calls the experiment
runner itself.
"""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

from .config import RunConfig, load_config
from .agents import stable_hash
from .health import run_health
from .logging import git_commit
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
    expected_run_prefix: str
    command: str
    config_hash: str | None
    probe_set_hash: str
    system_prompt_hash: str
    task_seed: int
    router_seed: int
    feedback_seed: int
    model: str
    backend: str
    omp_version_expected: str


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


def _omp_version() -> str:
    executable = shutil.which("omp")
    if not executable:
        return "unavailable (omp not on PATH during planning)"
    try:
        result = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable (version check failed)"
    return result.stdout.strip() if result.returncode == 0 else f"unavailable (exit {result.returncode})"


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
        probes, probe_set_hash = load_probe_set(base_config.logging.probe_set_path)
        counts = nominal_call_counts(base_config, len(probes))
        condition = base_config.condition.memory_mode
        task_seed = base_config.experiment.task_seed if base_config.experiment.task_seed is not None else base_config.experiment.seed
        router_seed = base_config.experiment.router_seed if base_config.experiment.router_seed is not None else base_config.experiment.seed + 1
        feedback_seed = base_config.experiment.feedback_seed if base_config.experiment.feedback_seed is not None else base_config.experiment.seed + 2
        omp_version = _omp_version()
        for seed in seeds:
            expected_prefix = f"{condition}-seed{seed}"
            command = " ".join(
                shlex.quote(part)
                for part in (
                    "./scripts/run-deepseek-experiment.sh", "--config", str(config_path),
                    "--seed", str(seed), "--output-dir", str(output_root),
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
                    output_dir=str(output_root),
                    expected_run_prefix=expected_prefix,
                    command=command,
                    config_hash=base_config.source_hash,
                    probe_set_hash=probe_set_hash,
                    system_prompt_hash=stable_hash(base_config.agent.system_prompt),
                    task_seed=seed if base_config.experiment.task_seed is None else base_config.experiment.task_seed,
                    router_seed=seed + 1 if base_config.experiment.router_seed is None else base_config.experiment.router_seed,
                    feedback_seed=seed + 2 if base_config.experiment.feedback_seed is None else base_config.experiment.feedback_seed,
                    model=base_config.agent.model,
                    backend=base_config.agent.backend,
                    omp_version_expected=omp_version,
                )
            )
    return planned


def _completed_match(row: PlannedRun, output_root: Path) -> Path | None:
    for run_dir in sorted(output_root.glob("*") if output_root.exists() else ()):
        if not run_dir.is_dir() or not (run_dir / "summary.json").is_file() or not (run_dir / "metadata.json").is_file():
            continue
        try:
            summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
            metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        config = metadata.get("config", {})
        if (
            summary.get("status") == "completed"
            and summary.get("condition") == row.condition
            and summary.get("seed") == row.seed
            and config.get("source_hash") == row.config_hash
        ):
            # A completed process is not necessarily a scientifically usable
            # run. Only a strict healthy artifact is resumable/skippable.
            try:
                if run_health(run_dir).get("health_flag") == "healthy":
                    return run_dir
            except (OSError, ValueError, KeyError):
                continue
    return None


def run_batch(
    planned: Iterable[PlannedRun],
    *,
    output_root: str | Path,
    only_seed: int | None = None,
    only_condition: str | None = None,
    confirm_real: bool = False,
) -> list[str]:
    """Run selected planned commands sequentially, skipping completed matches."""
    if not confirm_real:
        raise ValueError("real batch execution requires --confirm-real")
    root = Path(output_root)
    completed: list[str] = []
    for row in planned:
        if only_seed is not None and row.seed != only_seed:
            continue
        if only_condition is not None and row.condition != only_condition:
            continue
        existing = _completed_match(row, root)
        if existing is not None:
            print(f"SKIP completed: {existing}")
            completed.append(str(existing))
            continue
        subprocess.run(shlex.split(row.command), check=True)
    return completed


def plan_manifest(path: str | Path, planned: Iterable[PlannedRun]) -> dict[str, Any]:
    batch_path = Path(path).expanduser().resolve()
    rows = [asdict(row) for row in planned]
    return {
        "schema_version": 1,
        "batch_config": str(batch_path),
        "batch_config_hash": hashlib.sha256(batch_path.read_bytes()).hexdigest(),
        "git_commit": git_commit(),
        "expected_omp_version": rows[0]["omp_version_expected"] if rows else "unavailable",
        "runs": rows,
    }


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Plan a multi-seed experiment batch (no execution)")
    parser.add_argument("--config", required=True, help="Batch YAML path")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true", help="Print the dry plan (default)")
    mode.add_argument("--run", action="store_true", help="Run selected commands sequentially")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--confirm-real", action="store_true", help="Required safety acknowledgement for --run")
    parser.add_argument("--only-seed", type=int, help="Restrict --run to one seed")
    parser.add_argument("--only-condition", choices=["private", "shared"], help="Restrict --run to one condition")
    args = parser.parse_args(list(argv) if argv is not None else None)
    planned = plan_batch(args.config)
    selected = [
        row for row in planned
        if (args.only_seed is None or row.seed == args.only_seed)
        and (args.only_condition is None or row.condition == args.only_condition)
    ]
    if args.run:
        if not args.confirm_real:
            parser.error("--run requires --confirm-real; planning remains the safe default")
        batch_path = Path(args.config).expanduser().resolve()
        raw = yaml.safe_load(batch_path.read_text(encoding="utf-8")) or {}
        output_root = Path(str(raw.get("output_dir", "data/runs"))).expanduser()
        if not output_root.is_absolute():
            output_root = (Path.cwd() / output_root).resolve()
        run_batch(
            planned,
            output_root=output_root,
            only_seed=args.only_seed,
            only_condition=args.only_condition,
            confirm_real=args.confirm_real,
        )
        return
    rows = [asdict(row) for row in selected]
    if args.json:
        print(json.dumps(plan_manifest(args.config, selected), indent=2, sort_keys=True))
        return
    print("BATCH PLAN (no model calls)")
    print(f"git_commit={git_commit()}")
    print(f"expected omp={rows[0]['omp_version_expected'] if rows else 'unavailable'}")
    for row in rows:
        print(
            f"seed={row['seed']} condition={row['condition']} rounds={row['rounds']} "
            f"checkpoints={list(row['checkpoints'])} probes={row['probe_count']} "
            f"calls={row['nominal_calls']} (max={row['max_physical_calls']}) "
            f"output={row['output_dir']} prefix={row['expected_run_prefix']}"
        )
        print(f"  {row['command']}")


if __name__ == "__main__":
    main()
