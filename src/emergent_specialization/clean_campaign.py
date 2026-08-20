"""Resumable, explicitly gated runner for the clean response-semantics 2x2.

This module is intentionally separate from the historical v1 campaign runner.
It creates a new protocol identity and only searches its own output directory,
so legacy runs can never be silently reused.  ``--plan``/``--status``/``--cost``
are offline.  Real inference requires both ``--run`` and ``--confirm-real`` and
uses the DeepSeek Direct backend selected by the immutable YAML configs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from .config import RunConfig, load_config
from .health import run_health
from .logging import git_commit
from .probes import load_probe_set


CAMPAIGN_ID = "developmental-dynamics-v2"
PROTOCOL_VERSION = "staged-v3-response-semantics"
HARD_COST_CAP_USD = 2.00
MAX_PHYSICAL_ATTEMPTS = 40 * 700
SEEDS = tuple(range(1, 11))
CONFIGS = {
    ("confidence", "private"): "configs/research/v2/clean_confidence_private_20.yaml",
    ("confidence", "shared"): "configs/research/v2/clean_confidence_shared_20.yaml",
    ("random", "private"): "configs/research/v2/clean_random_private_20.yaml",
    ("random", "shared"): "configs/research/v2/clean_random_shared_20.yaml",
}
REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "data" / "campaigns" / CAMPAIGN_ID / "campaign.json"
RUN_ROOT = REPO_ROOT / "data" / "runs" / "campaigns" / CAMPAIGN_ID


@dataclass(frozen=True)
class PlannedRun:
    index: int
    seed: int
    router: str
    condition: str
    config_path: str
    config_hash: str
    protocol_version: str
    probe_set_hash: str
    nominal_logical_completions: int
    max_physical_attempts: int
    status: str = "planned"
    run_dir: str | None = None
    health: str | None = None
    return_code: int | None = None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def _config(path: str) -> tuple[RunConfig, Path, str, str]:
    absolute = (REPO_ROOT / path).resolve()
    config = load_config(absolute)
    probes, probe_hash = load_probe_set((REPO_ROOT / config.logging.probe_set_path).resolve())
    expected = config.experiment.num_rounds * config.experiment.num_agents
    expected += len(config.experiment.checkpoints) * len(probes) * config.experiment.num_agents
    if config.protocol_version != PROTOCOL_VERSION:
        raise ValueError(f"{path} has protocol_version={config.protocol_version!r}, expected {PROTOCOL_VERSION!r}")
    if config.agent.backend != "deepseek_direct":
        raise ValueError(f"{path} must use DeepSeek Direct, got {config.agent.backend!r}")
    if expected != 560:
        raise ValueError(f"{path} has {expected} nominal completions, expected 560")
    return config, absolute, probe_hash, _sha256(absolute)


def build_plan() -> list[PlannedRun]:
    rows: list[PlannedRun] = []
    index = 0
    # Deterministic paired ordering.  It is fixed in the manifest and never
    # depends on any scientific result.
    for seed in SEEDS:
        for router, condition in (
            ("confidence", "private"),
            ("confidence", "shared"),
            ("random", "private"),
            ("random", "shared"),
        ):
            config_path = CONFIGS[(router, condition)]
            config, absolute, probe_hash, config_hash = _config(config_path)
            rows.append(
                PlannedRun(
                    index=index,
                    seed=seed,
                    router=router,
                    condition=condition,
                    config_path=str(absolute.relative_to(REPO_ROOT)),
                    config_hash=config_hash,
                    protocol_version=config.protocol_version,
                    probe_set_hash=probe_hash,
                    nominal_logical_completions=560,
                    max_physical_attempts=700,
                )
            )
            index += 1
    return rows


def _read_manifest() -> dict[str, Any] | None:
    if not MANIFEST.exists():
        return None
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def create_manifest(*, force: bool = False) -> dict[str, Any]:
    existing = _read_manifest()
    if existing is not None and not force:
        if existing.get("campaign") != CAMPAIGN_ID or existing.get("protocol_version") != PROTOCOL_VERSION:
            raise ValueError("existing v2 manifest has an unexpected campaign/protocol identity")
        return existing
    if existing is not None and force and any(row.get("status") == "completed" for row in existing.get("runs", [])):
        raise ValueError("refusing to rebuild a manifest after execution has started")
    rows = build_plan()
    manifest = {
        "schema_version": 1,
        "campaign": CAMPAIGN_ID,
        "protocol_version": PROTOCOL_VERSION,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "starting_git_head": git_commit(),
        "provider": "deepseek_direct",
        "model": "deepseek-v4-flash",
        "credential_source": "keychain",
        "probe_set_hash": rows[0].probe_set_hash,
        "budget_policy": {
            "hard_cost_cap_usd": HARD_COST_CAP_USD,
            "max_physical_attempts": MAX_PHYSICAL_ATTEMPTS,
            "per_run_max_physical_attempts": 700,
            "max_attempts_per_logical_completion": 2,
        },
        "design": {
            "cells": ["confidence/private", "confidence/shared", "random/private", "random/shared"],
            "seeds": list(SEEDS),
            "agents": 4,
            "rounds": 20,
            "checkpoints": [0, 10, 20],
            "probes_per_checkpoint": 40,
            "nominal_completions_per_run": 560,
            "nominal_completions_total": 22400,
            "run_parallelism": 1,
        },
        "runs": [asdict(row) for row in rows],
        "state": {
            "status": "planned",
            "next_index": 0,
            "completed_runs": 0,
            "observed_cost_usd": 0.0,
            "physical_attempts": 0,
        },
        "legacy_reuse": "forbidden; only this campaign output root and exact v2 protocol/config identity may be reused",
    }
    _write_json(MANIFEST, manifest)
    return manifest


def _summary_cost(run_dir: Path) -> float:
    try:
        summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0.0
    usage = summary.get("usage") or {}
    for value in (usage.get("estimated_cost"), summary.get("observed_cost_usd")):
        if isinstance(value, (int, float)):
            return float(value)
    return 0.0


def _inventory_for(row: PlannedRun) -> tuple[Path, dict[str, Any]] | None:
    if not RUN_ROOT.exists():
        return None
    candidates: list[tuple[Path, dict[str, Any]]] = []
    for metadata_path in RUN_ROOT.glob("*/metadata.json"):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            summary_path = metadata_path.with_name("summary.json")
            summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
        except (OSError, json.JSONDecodeError):
            continue
        config = metadata.get("config") or {}
        experiment = config.get("experiment") or {}
        condition = (config.get("condition") or {}).get("memory_mode")
        router = (config.get("router") or {}).get("strategy")
        if (
            config.get("protocol_version") == PROTOCOL_VERSION
            and config.get("source_hash") == row.config_hash
            and int(experiment.get("seed", -1)) == row.seed
            and condition == row.condition
            and router == row.router
        ):
            candidates.append((metadata_path.parent, summary))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: str(item[0]))[-1]


def _health(run_dir: Path) -> dict[str, Any] | None:
    try:
        return run_health(run_dir)
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return None


def _refresh(manifest: dict[str, Any]) -> dict[str, Any]:
    total_cost = 0.0
    physical = 0
    completed = 0
    for raw in manifest["runs"]:
        row = PlannedRun(**raw)
        found = _inventory_for(row)
        if found is None:
            continue
        run_dir, summary = found
        health = _health(run_dir)
        if health is None:
            continue
        raw["run_dir"] = str(run_dir)
        raw["health"] = health.get("health_flag")
        raw["status"] = "completed" if summary.get("status") == "completed" and health.get("missing_logical_completions") == 0 else "incomplete"
        raw["return_code"] = 0 if raw["status"] == "completed" else raw.get("return_code")
        total_cost += _summary_cost(run_dir)
        physical += int(health.get("physical_attempts", 0))
        completed += raw["status"] == "completed"
    state = manifest.setdefault("state", {})
    state["completed_runs"] = completed
    state["observed_cost_usd"] = total_cost
    state["physical_attempts"] = physical
    state["next_index"] = next((int(raw["index"]) for raw in manifest["runs"] if raw["status"] not in {"completed"}), len(manifest["runs"]))
    state["status"] = "complete" if completed == len(manifest["runs"]) else state.get("status", "planned")
    return manifest


def _recent_cost_per_logical() -> float:
    """Use observed completed real runs only for a transparent forecast."""
    samples: list[float] = []
    for root in (REPO_ROOT / "data" / "runs" / "replication", REPO_ROOT / "data" / "runs" / "campaigns" / "developmental-dynamics-v1"):
        if not root.exists():
            continue
        for summary_path in root.glob("*/summary.json"):
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
                usage = summary.get("usage") or {}
                cost = usage.get("estimated_cost")
                calls = usage.get("calls_total")
                if summary.get("status") == "completed" and isinstance(cost, (int, float)) and isinstance(calls, int) and calls > 0:
                    samples.append(float(cost) / calls)
            except (OSError, json.JSONDecodeError):
                continue
    if not samples:
        raise RuntimeError("no observed completed real-run cost is available for forecasting")
    return sum(samples) / len(samples)


def _print_plan(manifest: dict[str, Any]) -> None:
    rows = manifest["runs"]
    per_run = rows[0]["nominal_logical_completions"]
    cost_per = _recent_cost_per_logical()
    print(f"campaign: {manifest['campaign']} protocol: {manifest['protocol_version']}")
    print(f"planned runs: {len(rows)} (4 cells × 10 seeds)")
    print(f"nominal completions/run: {per_run}")
    print(f"nominal total completions: {sum(row['nominal_logical_completions'] for row in rows)}")
    print(f"maximum physical attempts: {MAX_PHYSICAL_ATTEMPTS}")
    print(f"observed recent cost/completion: ${cost_per:.8f}")
    print(f"projected campaign cost: ${per_run * len(rows) * cost_per:.6f}")
    print(f"hard cost cap: ${HARD_COST_CAP_USD:.2f}")
    print(f"manifest: {MANIFEST}")


def _execute(manifest: dict[str, Any]) -> int:
    manifest = _refresh(manifest)
    cost = float(manifest["state"].get("observed_cost_usd") or 0.0)
    physical = int(manifest["state"].get("physical_attempts") or 0)
    if cost >= HARD_COST_CAP_USD or physical >= MAX_PHYSICAL_ATTEMPTS:
        manifest["state"]["status"] = "stopped_budget"
        _write_json(MANIFEST, manifest)
        print("STOPPED SAFELY: campaign budget/physical-attempt guard reached")
        return 2
    for raw in manifest["runs"]:
        row = PlannedRun(**raw)
        if raw["status"] == "completed":
            continue
        # A failed/incomplete row is never silently replaced.  It is resumed
        # in place only when its immutable v2 artifact is discoverable.
        found = _inventory_for(row)
        if found is not None and raw.get("status") == "incomplete":
            run_dir, _ = found
            command = [sys.executable, "-m", "emergent_specialization.experiment", "--resume", str(run_dir), "--confirm-real"]
        else:
            command = [sys.executable, "-m", "emergent_specialization.experiment", "--config", row.config_path, "--seed", str(row.seed), "--confirm-real"]
        print(f"RUN {row.index + 1}/{len(manifest['runs'])}: {row.router}/{row.condition} seed={row.seed}", flush=True)
        result = subprocess.run(command, cwd=REPO_ROOT, check=False)
        raw["return_code"] = result.returncode
        manifest = _refresh(manifest)
        _write_json(MANIFEST, manifest)
        current = next(item for item in manifest["runs"] if int(item["index"]) == row.index)
        if current["status"] != "completed":
            manifest["state"]["status"] = "stopped_incomplete"
            _write_json(MANIFEST, manifest)
            print(f"STOPPED: v2 run {row.index} is incomplete; preserve artifacts and inspect health", flush=True)
            return 3
        if float(manifest["state"].get("observed_cost_usd") or 0.0) >= HARD_COST_CAP_USD:
            manifest["state"]["status"] = "stopped_budget"
            _write_json(MANIFEST, manifest)
            print("STOPPED SAFELY: observed campaign cost reached hard cap", flush=True)
            return 2
        if int(manifest["state"].get("physical_attempts") or 0) >= MAX_PHYSICAL_ATTEMPTS:
            manifest["state"]["status"] = "stopped_budget"
            _write_json(MANIFEST, manifest)
            return 2
    manifest["state"]["status"] = "complete"
    _write_json(MANIFEST, manifest)
    print("CLEAN 2x2 CAMPAIGN COMPLETE", flush=True)
    return 0


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Plan/status/run the clean v2 response-semantics campaign")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--status", action="store_true")
    mode.add_argument("--cost", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--resume", action="store_true", help="Resume the v2 manifest; equivalent to --run")
    parser.add_argument("--confirm-real", action="store_true", help="Required for real DeepSeek Direct inference")
    parser.add_argument("--force", action="store_true", help="Create a new manifest only before execution")
    args = parser.parse_args(list(argv) if argv is not None else None)
    manifest = create_manifest(force=args.force)
    if args.plan:
        _print_plan(manifest)
        return
    if args.status:
        _refresh(manifest)
        _write_json(MANIFEST, manifest)
        print(json.dumps(manifest["state"], indent=2, sort_keys=True))
        return
    if args.cost:
        _refresh(manifest)
        _write_json(MANIFEST, manifest)
        print(json.dumps({"observed_cost_usd": manifest["state"].get("observed_cost_usd"), "hard_cap_usd": HARD_COST_CAP_USD, "physical_attempts": manifest["state"].get("physical_attempts"), "physical_ceiling": MAX_PHYSICAL_ATTEMPTS}, indent=2, sort_keys=True))
        return
    if not args.confirm_real:
        raise SystemExit("real v2 execution requires --confirm-real")
    raise SystemExit(_execute(manifest))


if __name__ == "__main__":
    main()
