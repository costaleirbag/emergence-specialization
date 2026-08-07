"""Resumable, sequential campaign orchestration with a hard cost guard.

The campaign planner is deliberately conservative: planning and inventory are
offline, and real execution requires an explicit ``--confirm-real`` in both
this module and the experiment CLI.  The manifest separates an immutable plan
from mutable execution state so an interrupted campaign can be resumed without
rerunning healthy logical completions.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from .batch import nominal_call_counts
from .config import RunConfig, load_config
from .health import run_health
from .logging import git_commit
from .probes import load_probe_set


CAMPAIGN_ID = "developmental-dynamics-v1"
HARD_COST_CAP_USD = 7.50
REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_RELATIVE = Path("data/campaigns") / CAMPAIGN_ID / "campaign.json"
RUN_ROOT_RELATIVE = Path("data/runs/campaigns") / CAMPAIGN_ID
REPORT_ROOT_RELATIVE = Path("reports/campaigns") / CAMPAIGN_ID


@dataclass(frozen=True)
class CampaignRun:
    stage: str
    seed: int
    condition: str
    router: str
    config_path: str
    config_hash: str
    probe_set_hash: str
    nominal_calls: int
    max_physical_calls: int
    interaction_calls: int
    probe_calls: int
    status: str = "planned"
    run_dir: str | None = None
    health: str | None = None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _resolve(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    return candidate if candidate.is_absolute() else (REPO_ROOT / candidate).resolve()


def manifest_path(root: str | Path = REPO_ROOT) -> Path:
    return _resolve(Path(root) / MANIFEST_RELATIVE)


def _config_for(path: str | Path) -> tuple[RunConfig, Path, str, str]:
    absolute = _resolve(path)
    config = load_config(absolute)
    probes, probe_hash = load_probe_set(_resolve(config.logging.probe_set_path))
    return config, absolute, probe_hash, _sha256(absolute)


def _matching_existing_runs(config_hash: str, condition: str, seed: int) -> list[tuple[Path, dict[str, Any]]]:
    matches: list[tuple[Path, dict[str, Any]]] = []
    roots = [REPO_ROOT / "data" / "runs", REPO_ROOT / "data" / "smoke_runs"]
    for root in roots:
        if not root.exists():
            continue
        for metadata_path in root.rglob("metadata.json"):
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                summary_path = metadata_path.with_name("summary.json")
                summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
            except (OSError, json.JSONDecodeError):
                continue
            config = metadata.get("config") or {}
            if (
                config.get("source_hash") == config_hash
                and summary.get("condition", config.get("condition", {}).get("memory_mode")) == condition
                and int(summary.get("seed", config.get("experiment", {}).get("seed", -1))) == seed
            ):
                matches.append((metadata_path.parent, summary))
    return sorted(matches, key=lambda item: str(item[0]))


def _reuse_candidate(row: CampaignRun) -> tuple[Path, dict[str, Any]] | None:
    for run_dir, summary in _matching_existing_runs(row.config_hash, row.condition, row.seed):
        try:
            health = run_health(run_dir)
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            continue
        if summary.get("status") == "completed" and health["health_flag"] in {"healthy", "healthy_recovered"}:
            return run_dir, health
    return None


def _row(stage: str, seed: int, config_path: str) -> CampaignRun:
    config, absolute, probe_hash, config_hash = _config_for(config_path)
    probes, _ = load_probe_set(_resolve(config.logging.probe_set_path))
    counts = nominal_call_counts(config, len(probes))
    if config.agent.backend != "deepseek_direct":
        raise ValueError(f"campaign configs must use DeepSeek Direct, got {config.agent.backend!r}")
    return CampaignRun(
        stage=stage,
        seed=seed,
        condition=config.condition.memory_mode,
        router=config.router.strategy,
        config_path=str(absolute.relative_to(REPO_ROOT)),
        config_hash=config_hash,
        probe_set_hash=probe_hash,
        nominal_calls=counts["nominal_calls"],
        max_physical_calls=counts["max_physical_calls"],
        interaction_calls=counts["interaction_calls"],
        probe_calls=counts["probe_calls"],
    )


def build_campaign_plan() -> list[CampaignRun]:
    """Expand the pre-registered three-stage campaign deterministically."""
    rows: list[CampaignRun] = []
    # Existing seed 1 is discovered and reused; seeds 2..100 are new.
    for seed in range(1, 101):
        rows.append(_row("A", seed, "configs/research/replication_private.yaml"))
        rows.append(_row("A", seed, "configs/research/replication_shared.yaml"))
    for seed in range(1, 51):
        rows.append(_row("B", seed, "configs/research/campaigns/random_private_20.yaml"))
        rows.append(_row("B", seed, "configs/research/campaigns/random_shared_20.yaml"))
    for seed in range(1001, 1011):
        rows.append(_row("C", seed, "configs/research/campaigns/long_private_100.yaml"))
        rows.append(_row("C", seed, "configs/research/campaigns/long_shared_100.yaml"))
    return rows


def _usage_cost(run_dir: Path) -> float:
    try:
        summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0.0
    usage = summary.get("usage") or {}
    value = usage.get("estimated_cost")
    if isinstance(value, (int, float)):
        return float(value)
    value = summary.get("observed_cost_usd")
    return float(value) if isinstance(value, (int, float)) else 0.0


def observed_baseline_cost_per_logical() -> float:
    """Estimate a logical-completion cost from the two existing seed-1 runs."""
    total_cost = 0.0
    total_calls = 0
    for condition in ("private", "shared"):
        candidates = [
            p for p, _ in _matching_existing_runs(
                _config_for(f"configs/research/replication_{condition}.yaml")[3], condition, 1
            )
        ]
        for run_dir in candidates:
            health = run_health(run_dir)
            if health["health_flag"] in {"healthy", "healthy_recovered"}:
                total_cost += _usage_cost(run_dir)
                total_calls += int(health["expected_logical_completions"])
                break
    if not total_calls:
        raise RuntimeError("no healthy observed baseline run is available for cost forecasting")
    return total_cost / total_calls


def _apply_reuse(rows: list[CampaignRun]) -> tuple[list[CampaignRun], list[dict[str, Any]]]:
    updated: list[CampaignRun] = []
    reused: list[dict[str, Any]] = []
    for row in rows:
        candidate = _reuse_candidate(row) if row.stage == "A" and row.seed == 1 else None
        if candidate is None:
            updated.append(row)
            continue
        run_dir, health = candidate
        updated.append(
            CampaignRun(**{**asdict(row), "status": "reused", "run_dir": str(run_dir), "health": health["health_flag"]})
        )
        reused.append({"stage": row.stage, "seed": row.seed, "condition": row.condition, "run_dir": str(run_dir), "health": health})
    return updated, reused


def _forecast(rows: list[CampaignRun], cost_per_logical: float) -> dict[str, float | int]:
    new_rows = [row for row in rows if row.status not in {"reused", "completed"}]
    logical = sum(row.nominal_calls for row in new_rows)
    return {
        "new_runs": len(new_rows),
        "new_logical_completions": logical,
        "projected_cost_usd": logical * cost_per_logical,
        "cost_per_logical_completion_usd": cost_per_logical,
    }


def _stage_counts(rows: list[CampaignRun]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for stage in ("A", "B", "C"):
        selected = [row for row in rows if row.stage == stage]
        result[stage] = {
            "planned_runs": len(selected),
            "reused_runs": sum(row.status == "reused" for row in selected),
            "nominal_logical_completions": sum(row.nominal_calls for row in selected),
            "max_physical_attempts": sum(row.max_physical_calls for row in selected),
        }
    return result


def create_manifest(*, force: bool = False) -> dict[str, Any]:
    path = manifest_path()
    if path.exists() and not force:
        return json.loads(path.read_text(encoding="utf-8"))
    if path.exists() and force:
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("state", {}).get("status") not in {"ready", "blocked_budget_forecast"}:
            raise ValueError("refusing to rebuild a campaign manifest after execution has started")
    rows, reused = _apply_reuse(build_campaign_plan())
    cost_per_logical = observed_baseline_cost_per_logical()
    forecast = _forecast(rows, cost_per_logical)
    probe_hashes = sorted({row.probe_set_hash for row in rows})
    if len(probe_hashes) != 1:
        raise ValueError(f"campaign configs do not share one probe set hash: {probe_hashes}")
    manifest = {
        "schema_version": 1,
        "campaign_id": CAMPAIGN_ID,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "starting_git_head": git_commit(),
        "provider": "deepseek_direct",
        "model": "deepseek-v4-flash",
        "credential_source": "keychain",
        "probe_set_hash": probe_hashes[0],
        "budget": {
            "hard_observed_cost_cap_usd": HARD_COST_CAP_USD,
            "observed_campaign_cost_usd": 0.0,
            "physical_attempt_ceiling": sum(row.max_physical_calls for row in rows if row.status != "reused"),
        },
        "forecast": forecast,
        "stage_counts": _stage_counts(rows),
        "existing_runs_reused": reused,
        "stage_definitions": {
            "A": {"conditions": ["private", "shared"], "router": "confidence", "seeds": list(range(1, 101)), "new_seeds": list(range(2, 101)), "rounds": 20, "checkpoints": [0, 10, 20], "probes_per_checkpoint": 40},
            "B": {"conditions": ["private", "shared"], "router": "random", "seeds": list(range(1, 51)), "rounds": 20, "checkpoints": [0, 10, 20], "probes_per_checkpoint": 40},
            "C": {"conditions": ["private", "shared"], "router": "confidence", "seeds": list(range(1001, 1011)), "rounds": 100, "checkpoints": list(range(0, 101, 10)), "probes_per_checkpoint": 40},
        },
        "state": {"status": "blocked_budget_forecast" if forecast["projected_cost_usd"] > HARD_COST_CAP_USD else "ready", "current_index": 0, "completed_runs": len(reused), "physical_attempts": 0},
        "runs": [asdict(row) for row in rows],
    }
    _json_write(path, manifest)
    return manifest


def _refresh_cost(manifest: dict[str, Any]) -> float:
    total = 0.0
    for row in manifest["runs"]:
        # Seed-1 baseline artifacts are provenance inputs, not spend from this
        # campaign's remaining budget.
        if row.get("run_dir") and row.get("status") != "reused":
            total += _usage_cost(Path(row["run_dir"]))
    manifest["budget"]["observed_campaign_cost_usd"] = total
    return total


def _write_reports(manifest: dict[str, Any]) -> None:
    report_root = REPO_ROOT / REPORT_ROOT_RELATIVE
    report_root.mkdir(parents=True, exist_ok=True)
    inventory: list[dict[str, Any]] = []
    tidy_rows: list[dict[str, Any]] = []
    for row in manifest["runs"]:
        item = dict(row)
        if row.get("run_dir"):
            run_dir = Path(row["run_dir"])
            try:
                health = run_health(run_dir)
                item.update({"health": health["health_flag"], "status": health["status"], "physical_attempts": health["physical_attempts"], "retries": health["retries"], "observed_cost_usd": health.get("observed_cost_usd")})
            except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
                item.update({"health": "unreadable", "health_error": str(exc)})
            metrics_path = run_dir / "metrics.jsonl"
            if metrics_path.exists():
                for line in metrics_path.read_text(encoding="utf-8").splitlines():
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    checkpoint = payload.get("checkpoint")
                    for key, value in payload.items():
                        if isinstance(value, (int, float)):
                            tidy_rows.append({"campaign": CAMPAIGN_ID, "stage": row["stage"], "condition": row["condition"], "router": row["router"], "seed": row["seed"], "checkpoint": checkpoint, "run_id": Path(row["run_dir"]).name, "metric_name": key, "metric_value": value})
        inventory.append(item)
    _json_write(report_root / "run_inventory.json", inventory)
    for stage in ("A", "B", "C"):
        stage_root = report_root / f"stage-{stage.lower()}"
        stage_root.mkdir(parents=True, exist_ok=True)
        _json_write(stage_root / "run_inventory.json", [item for item in inventory if item["stage"] == stage])
    with (report_root / "run_inventory.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["stage", "seed", "condition", "router", "status", "health", "run_dir", "nominal_calls", "physical_attempts", "retries", "observed_cost_usd"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: item.get(field) for field in fields} for item in inventory)
    with (report_root / "tidy_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["campaign", "stage", "condition", "router", "seed", "checkpoint", "run_id", "metric_name", "metric_value"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(tidy_rows)


def _print_plan(manifest: dict[str, Any]) -> None:
    print(json.dumps({key: manifest[key] for key in ("campaign_id", "starting_git_head", "model", "provider", "probe_set_hash", "budget", "forecast", "stage_counts", "state")}, indent=2, sort_keys=True))
    print("planned runs:", len(manifest["runs"]))
    print("reused runs:", len(manifest["existing_runs_reused"]))


def run_campaign(manifest: dict[str, Any]) -> int:
    forecast = manifest["forecast"]
    if float(forecast["projected_cost_usd"]) > HARD_COST_CAP_USD:
        manifest["state"].update({"status": "blocked_budget_forecast"})
        _json_write(manifest_path(), manifest)
        _write_reports(manifest)
        print(f"STOP BEFORE REAL CALLS: projected cost ${forecast['projected_cost_usd']:.4f} exceeds hard cap ${HARD_COST_CAP_USD:.2f}")
        return 2
    for index, row in enumerate(manifest["runs"]):
        if row.get("status") in {"reused", "completed"}:
            continue
        observed = _refresh_cost(manifest)
        if observed >= HARD_COST_CAP_USD:
            manifest["state"].update({"status": "stopped_budget"})
            _json_write(manifest_path(), manifest)
            return 2
        pending_logical = sum(
            int(item["nominal_calls"])
            for item in manifest["runs"][index:]
            if item.get("status") not in {"reused", "completed"}
        )
        projected_remaining = observed + pending_logical * float(manifest["forecast"]["cost_per_logical_completion_usd"])
        if projected_remaining > HARD_COST_CAP_USD:
            manifest["state"].update({"status": "stopped_budget_forecast"})
            _json_write(manifest_path(), manifest)
            print(f"STOP BEFORE REAL CALLS: remaining forecast ${projected_remaining:.4f} exceeds hard cap ${HARD_COST_CAP_USD:.2f}")
            return 2
        row["status"] = "running"
        manifest["state"].update({"status": "running", "current_index": index})
        _json_write(manifest_path(), manifest)
        config_path = _resolve(row["config_path"])
        command = [sys.executable, "-m", "emergent_specialization.experiment", "--config", str(config_path), "--seed", str(row["seed"]), "--output-dir", str(REPO_ROOT / RUN_ROOT_RELATIVE), "--confirm-real"]
        print(f"CAMPAIGN {row['stage']} {row['condition']} seed {row['seed']} — {row['nominal_calls']} logical completions", flush=True)
        result = subprocess.run(command, cwd=REPO_ROOT, check=False)
        if result.returncode != 0:
            row["status"] = "failed"
            manifest["state"].update({"status": "stopped_runtime_error"})
            _json_write(manifest_path(), manifest)
            _write_reports(manifest)
            return result.returncode or 1
        candidates = []
        root = REPO_ROOT / RUN_ROOT_RELATIVE
        for metadata_path in root.rglob("metadata.json") if root.exists() else ():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                summary = json.loads((metadata_path.parent / "summary.json").read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if int(summary.get("seed", -1)) == row["seed"] and summary.get("condition") == row["condition"] and metadata.get("config", {}).get("source_hash") == row["config_hash"]:
                candidates.append(metadata_path.parent)
        if not candidates:
            row["status"] = "invalid"
            manifest["state"].update({"status": "stopped_missing_artifact"})
            _json_write(manifest_path(), manifest)
            return 1
        run_dir = sorted(candidates, key=lambda p: p.stat().st_mtime)[-1]
        health = run_health(run_dir)
        row.update({"status": "completed" if health["health_flag"] in {"healthy", "healthy_recovered"} else "invalid", "run_dir": str(run_dir), "health": health["health_flag"]})
        manifest["state"].update({"completed_runs": sum(item.get("status") in {"completed", "reused"} for item in manifest["runs"]), "physical_attempts": sum(int(item.get("physical_attempts", 0) or 0) for item in manifest["runs"] if item.get("status") != "reused")})
        _refresh_cost(manifest)
        _json_write(manifest_path(), manifest)
        _write_reports(manifest)
        if row["status"] == "invalid":
            manifest["state"].update({"status": "stopped_invalid_run"})
            _json_write(manifest_path(), manifest)
            return 1
    manifest["state"].update({"status": "complete"})
    _json_write(manifest_path(), manifest)
    _write_reports(manifest)
    return 0


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Plan or run the guarded developmental-dynamics campaign")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true", help="create/print the immutable plan; never calls a model")
    mode.add_argument("--run", action="store_true", help="execute pending runs sequentially")
    mode.add_argument("--resume", action="store_true", help="resume the manifest in place")
    parser.add_argument("--confirm-real", action="store_true", help="required for real DeepSeek Direct execution")
    parser.add_argument("--force-manifest", action="store_true", help="rebuild only when no real campaign has started")
    args = parser.parse_args(list(argv) if argv is not None else None)
    manifest = create_manifest(force=args.force_manifest)
    _print_plan(manifest)
    if args.run or args.resume:
        if not args.confirm_real:
            raise SystemExit("real campaign execution requires --confirm-real")
        raise SystemExit(run_campaign(manifest))


if __name__ == "__main__":
    main()
