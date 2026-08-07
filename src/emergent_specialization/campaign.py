"""Human-gated, resumable campaign planning and offline reporting.

Planning, status, approval, inventory and interim reports are offline by
construction.  A real run requires the explicit ``--run-gate`` plus
``--confirm-real`` flags.  Scientific gates never unlock themselves from a
metric, p-value or effect estimate.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterable

from .aggregate import aggregate_runs
from .analysis import checkpoint_rows, hse_trajectory_rows, load_run
from .batch import nominal_call_counts
from .config import RunConfig, load_config
from .health import run_health
from .logging import git_commit
from .probes import load_probe_set


CAMPAIGN_ID = "developmental-dynamics-v1"
PROTOCOL_VERSION = "staged-v2"
GATE_1 = "gate_1_replication"
GATE_2 = "gate_2_replication"
HARD_COST_CAP_USD = 7.50  # legacy full-campaign cap; no longer an execution authorization
GATE_1_HARD_BUDGET_USD = 1.00
FUTURE_BUDGET_REFERENCE_USD = 8.80
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
    gate: str = GATE_1
    identity: str = ""
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


def _resolve(path: str | Path, *, root: Path = REPO_ROOT) -> Path:
    candidate = Path(path).expanduser()
    return candidate if candidate.is_absolute() else (root / candidate).resolve()


def manifest_path(root: str | Path = REPO_ROOT) -> Path:
    return _resolve(Path(root) / MANIFEST_RELATIVE)


def _config_for(path: str | Path) -> tuple[RunConfig, Path, str, str]:
    absolute = _resolve(path)
    config = load_config(absolute)
    _, probe_hash = load_probe_set(_resolve(config.logging.probe_set_path))
    return config, absolute, probe_hash, _sha256(absolute)


def _matching_existing_runs(config_hash: str, condition: str, seed: int) -> list[tuple[Path, dict[str, Any]]]:
    """Find exact scientific identities without trusting directory names."""
    matches: list[tuple[Path, dict[str, Any]]] = []
    for root in (REPO_ROOT / "data" / "runs", REPO_ROOT / "data" / "smoke_runs"):
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
            summary_condition = summary.get("condition", config.get("condition", {}).get("memory_mode"))
            summary_seed = summary.get("seed", config.get("experiment", {}).get("seed", -1))
            if config.get("source_hash") == config_hash and summary_condition == condition and int(summary_seed) == seed:
                matches.append((metadata_path.parent, summary))
    return sorted(matches, key=lambda item: str(item[0]))


def _health_for(run_dir: Path) -> dict[str, Any] | None:
    try:
        return run_health(run_dir)
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return None


def _reuse_candidate(row: CampaignRun) -> tuple[Path, dict[str, Any]] | None:
    for run_dir, summary in _matching_existing_runs(row.config_hash, row.condition, row.seed):
        health = _health_for(run_dir)
        if summary.get("status") == "completed" and health and health["health_flag"] in {"healthy", "healthy_recovered"}:
            return run_dir, health
    return None


def _incomplete_candidate(row: CampaignRun) -> tuple[Path, dict[str, Any]] | None:
    for run_dir, summary in _matching_existing_runs(row.config_hash, row.condition, row.seed):
        health = _health_for(run_dir)
        if summary.get("status") != "completed" and health:
            return run_dir, health
    return None


def _row(stage: str, seed: int, config_path: str) -> CampaignRun:
    config, absolute, probe_hash, config_hash = _config_for(config_path)
    probes, _ = load_probe_set(_resolve(config.logging.probe_set_path))
    counts = nominal_call_counts(config, len(probes))
    if config.agent.backend != "deepseek_direct":
        raise ValueError(f"campaign configs must use DeepSeek Direct, got {config.agent.backend!r}")
    condition = config.condition.memory_mode
    identity = ":".join((CAMPAIGN_ID, PROTOCOL_VERSION, stage, str(seed), condition, config_hash))
    gate = GATE_1 if stage == "A" and seed <= 10 else GATE_2 if stage == "A" and seed <= 50 else (
        "candidate_random_routing" if stage == "B" else "candidate_long_horizon"
    )
    return CampaignRun(
        stage=stage,
        seed=seed,
        condition=condition,
        router=config.router.strategy,
        config_path=str(absolute.relative_to(REPO_ROOT)),
        config_hash=config_hash,
        probe_set_hash=probe_hash,
        nominal_calls=counts["nominal_calls"],
        max_physical_calls=counts["max_physical_calls"],
        interaction_calls=counts["interaction_calls"],
        probe_calls=counts["probe_calls"],
        gate=gate,
        identity=identity,
    )


def build_campaign_plan() -> list[CampaignRun]:
    """Expand all pre-registered baseline/candidate identities deterministically."""
    rows: list[CampaignRun] = []
    for seed in range(1, 101):
        rows.extend((_row("A", seed, "configs/research/replication_private.yaml"), _row("A", seed, "configs/research/replication_shared.yaml")))
    for seed in range(1, 51):
        rows.extend((_row("B", seed, "configs/research/campaigns/random_private_20.yaml"), _row("B", seed, "configs/research/campaigns/random_shared_20.yaml")))
    for seed in range(1001, 1011):
        rows.extend((_row("C", seed, "configs/research/campaigns/long_private_100.yaml"), _row("C", seed, "configs/research/campaigns/long_shared_100.yaml")))
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
    total_cost = 0.0
    total_calls = 0
    for condition in ("private", "shared"):
        config_hash = _config_for(f"configs/research/replication_{condition}.yaml")[3]
        for run_dir, _ in _matching_existing_runs(config_hash, condition, 1):
            health = _health_for(run_dir)
            if health and health["health_flag"] in {"healthy", "healthy_recovered"}:
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
        updated_row = CampaignRun(**{**asdict(row), "status": "reused", "run_dir": str(run_dir), "health": health["health_flag"]})
        updated.append(updated_row)
        reused.append({"stage": row.stage, "seed": row.seed, "condition": row.condition, "run_dir": str(run_dir), "health": health})
    return updated, reused


def _forecast(rows: list[CampaignRun], cost_per_logical: float) -> dict[str, float | int]:
    new_rows = [row for row in rows if row.status not in {"reused", "completed"}]
    logical = sum(row.nominal_calls for row in new_rows)
    return {"new_runs": len(new_rows), "new_logical_completions": logical, "projected_cost_usd": logical * cost_per_logical, "cost_per_logical_completion_usd": cost_per_logical}


def _gate_summary(rows: list[CampaignRun], gate: str, cost_per_logical: float) -> dict[str, Any]:
    selected = [row for row in rows if row.gate == gate]
    active = [row for row in selected if row.status not in {"reused", "completed"}]
    nominal = sum(row.nominal_calls for row in active)
    reused = sum(row.status == "reused" for row in selected)
    pairs = sorted({row.seed for row in selected})
    return {
        "gate": gate,
        "planned_paired_seeds": len(pairs),
        "new_runs": len(active),
        "reused_runs": reused,
        "new_paired_seeds": len({row.seed for row in active}),
        "nominal_logical_completions": nominal,
        "expected_nominal_cost_usd": nominal * cost_per_logical,
        "cost_per_logical_completion_usd": cost_per_logical,
        "hard_budget_usd": GATE_1_HARD_BUDGET_USD if gate == GATE_1 else None,
        "max_physical_attempts": sum(row.max_physical_calls for row in active),
    }


def _stage_counts(rows: list[CampaignRun]) -> dict[str, dict[str, int]]:
    return {
        stage: {
            "planned_runs": sum(row.stage == stage for row in rows),
            "reused_runs": sum(row.stage == stage and row.status == "reused" for row in rows),
            "nominal_logical_completions": sum(row.nominal_calls for row in rows if row.stage == stage),
            "max_physical_attempts": sum(row.max_physical_calls for row in rows if row.stage == stage and row.status != "reused"),
        }
        for stage in ("A", "B", "C")
    }


def _gate_definition(rows: list[CampaignRun], gate: str, cost_per_logical: float) -> dict[str, Any]:
    summary = _gate_summary(rows, gate, cost_per_logical)
    seeds = sorted({row.seed for row in rows if row.gate == gate})
    return {
        **summary,
        "status": "planned" if gate == GATE_1 else "locked",
        "seeds": seeds,
        "conditions": ["private", "shared"],
        "requires_human_confirmation": True,
        "depends_on": ["human_review_gate_1"] if gate == GATE_2 else [],
        "target_total_paired_seeds": 50 if gate == GATE_2 else 10,
    }


def create_manifest(*, force: bool = False) -> dict[str, Any]:
    path = manifest_path()
    if path.exists() and not force:
        existing = json.loads(path.read_text(encoding="utf-8"))
        if int(existing.get("schema_version", 1)) >= 2:
            return existing
        # The previous v1 manifest only planned runs and had not started any
        # paid execution, so it can be migrated into the staged schema.
        if existing.get("state", {}).get("status") not in {None, "ready", "blocked_budget_forecast"}:
            raise ValueError("refusing to migrate a campaign after execution has started")
    if path.exists() and force:
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("state", {}).get("status") not in {None, "ready", "blocked_budget_forecast", "gate_1_planned"}:
            raise ValueError("refusing to rebuild a campaign manifest after execution has started")
    rows, reused = _apply_reuse(build_campaign_plan())
    cost_per_logical = observed_baseline_cost_per_logical()
    probe_hashes = sorted({row.probe_set_hash for row in rows})
    if len(probe_hashes) != 1:
        raise ValueError(f"campaign configs do not share one probe set hash: {probe_hashes}")
    serialized: list[dict[str, Any]] = []
    for row in rows:
        item = asdict(row)
        if row.gate == GATE_1:
            pass
        elif row.gate == GATE_2:
            item["status"] = "locked"
        else:
            item["status"] = "optional"
        if row.status == "reused":
            item["status"] = "reused"
        serialized.append(item)
    gate1_rows = [CampaignRun(**item) for item in serialized if item["gate"] == GATE_1]
    gate2_rows = [CampaignRun(**item) for item in serialized if item["gate"] == GATE_2]
    all_new = [row for row in rows if row.status != "reused"]
    manifest = {
        "schema_version": 2,
        "campaign": CAMPAIGN_ID,
        "protocol_version": PROTOCOL_VERSION,
        "base_commit": git_commit(),
        "created_at_utc": datetime.now(UTC).isoformat(),
        "provider": "deepseek_direct",
        "model": "deepseek-v4-flash",
        "credential_source": "keychain",
        "probe_set_hash": probe_hashes[0],
        "budget_policy": {
            "gate_1_hard_budget_usd": GATE_1_HARD_BUDGET_USD,
            "future_reference_budget_usd": FUTURE_BUDGET_REFERENCE_USD,
            "legacy_full_campaign_cap_usd": HARD_COST_CAP_USD,
            "no_automatic_full_campaign_authorization": True,
        },
        "cost_forecast": {
            "cost_per_logical_completion_usd": cost_per_logical,
            "gate_1": _gate_summary(gate1_rows, GATE_1, cost_per_logical),
            "gate_2_incremental": _gate_summary(gate2_rows, GATE_2, cost_per_logical),
            "candidate_random_routing": {"nominal_logical_completions": sum(row.nominal_calls for row in rows if row.stage == "B"), "expected_cost_usd": sum(row.nominal_calls for row in rows if row.stage == "B") * cost_per_logical},
            "candidate_long_horizon": {"nominal_logical_completions": sum(row.nominal_calls for row in rows if row.stage == "C"), "expected_cost_usd": sum(row.nominal_calls for row in rows if row.stage == "C") * cost_per_logical},
        },
        "stage_counts": _stage_counts(rows),
        "existing_runs_reused": reused,
        "gates": {
            GATE_1: _gate_definition(gate1_rows, GATE_1, cost_per_logical),
            GATE_2: _gate_definition(gate2_rows, GATE_2, cost_per_logical),
            "candidate_random_routing": {"status": "optional", "depends_on": ["human_review_gate_1"]},
            "candidate_long_horizon": {"status": "optional", "depends_on": ["human_review_gate_1", "human_review_gate_2"]},
        },
        "state": {"status": "gate_1_planned", "active_gate": GATE_1, "current_index": 0, "completed_runs": len(reused), "physical_attempts": 0, "observed_cost_usd": 0.0},
        "human_approvals": [],
        "runs": serialized,
        "duplicate_policy": "match campaign/protocol/seed/condition/config_hash; reuse healthy, resume incomplete, never overwrite",
        "health_policy": {"clean": "100% logical coverage and no retry/error", "recovered": "100% logical coverage with recovered technical errors", "invalid": "missing logical completions or failed run"},
    }
    _json_write(path, manifest)
    return manifest


def _manifest_file(manifest: dict[str, Any], value: str | Path | None = None) -> Path:
    return _resolve(value) if value is not None else manifest_path()


def _rows_for_gate(manifest: dict[str, Any], gate: str) -> list[dict[str, Any]]:
    return [row for row in manifest.get("runs", []) if row.get("gate") == gate]


def _refresh_cost(manifest: dict[str, Any], gate: str | None = None) -> float:
    total = 0.0
    for row in manifest.get("runs", []):
        if gate and row.get("gate") != gate:
            continue
        if row.get("run_dir") and row.get("status") != "reused":
            total += _usage_cost(Path(row["run_dir"]))
    manifest.setdefault("state", {})["observed_cost_usd"] = total
    if gate:
        manifest.setdefault("gates", {}).setdefault(gate, {})["observed_cost_usd"] = total
    return total


def _reconcile_rows(manifest: dict[str, Any], gate: str) -> None:
    for row in _rows_for_gate(manifest, gate):
        if row.get("status") in {"reused", "completed", "locked", "optional"}:
            continue
        candidate = _reuse_candidate(CampaignRun(**row))
        if candidate:
            run_dir, health = candidate
            row.update({"status": "reused", "run_dir": str(run_dir), "health": health["health_flag"]})
            continue
        incomplete = _incomplete_candidate(CampaignRun(**row))
        if incomplete:
            run_dir, health = incomplete
            row.update({"status": "incomplete", "run_dir": str(run_dir), "health": health["health_flag"]})


def _accepted(row: dict[str, Any]) -> bool:
    return row.get("status") in {"reused", "completed"} and row.get("health") in {"healthy", "healthy_recovered"}


def _pair_rows(manifest: dict[str, Any], gate: str) -> dict[int, dict[str, dict[str, Any]]]:
    pairs: dict[int, dict[str, dict[str, Any]]] = {}
    for row in _rows_for_gate(manifest, gate):
        pairs.setdefault(int(row["seed"]), {})[str(row["condition"])] = row
    return pairs


def _pair_health(manifest: dict[str, Any], gate: str) -> dict[str, Any]:
    pairs = _pair_rows(manifest, gate)
    complete: list[int] = []
    incomplete: list[int] = []
    for seed, rows in sorted(pairs.items()):
        if all(_accepted(rows.get(condition, {})) for condition in ("private", "shared")):
            complete.append(seed)
        else:
            incomplete.append(seed)
    return {"complete_pair_seeds": complete, "incomplete_pair_seeds": incomplete, "complete_pairs": len(complete), "incomplete_pairs": len(incomplete)}


def _select_pending_pairs(manifest: dict[str, Any], gate: str, max_new_pairs: int | None) -> list[int]:
    pairs = _pair_rows(manifest, gate)
    complete = set(_pair_health(manifest, gate)["complete_pair_seeds"])
    pending = [seed for seed in sorted(pairs) if seed not in complete]
    # --max-new-pairs means new paired seeds, not conditions. Existing/reused
    # seed 1 therefore does not consume a tranche slot.
    if max_new_pairs is not None:
        if max_new_pairs < 1:
            raise ValueError("max_new_pairs must be positive")
        pending = pending[:max_new_pairs]
    return pending


def _discover_campaign_run(row: dict[str, Any], run_root: Path) -> Path | None:
    candidates: list[Path] = []
    if run_root.exists():
        for metadata_path in run_root.rglob("metadata.json"):
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                summary = json.loads((metadata_path.parent / "summary.json").read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if int(summary.get("seed", -1)) == int(row["seed"]) and summary.get("condition") == row["condition"] and metadata.get("config", {}).get("source_hash") == row["config_hash"]:
                candidates.append(metadata_path.parent)
    return sorted(candidates, key=lambda path: path.stat().st_mtime)[-1] if candidates else None


def _run_one_row(
    row: dict[str, Any],
    *,
    mock: bool,
    run_root: Path,
    executor: Callable[[list[str]], int] | None = None,
) -> bool:
    if _accepted(row):
        return True
    if row.get("run_dir") and row.get("status") == "incomplete":
        command = [sys.executable, "-m", "emergent_specialization.experiment", "--resume", str(row["run_dir"])]
    else:
        command = [sys.executable, "-m", "emergent_specialization.experiment", "--config", str(_resolve(row["config_path"])), "--seed", str(row["seed"]), "--output-dir", str(run_root)]
    if mock:
        command.append("--dry-run")
    else:
        command.append("--confirm-real")
    code = executor(command) if executor else subprocess.run(command, cwd=REPO_ROOT, check=False).returncode
    if code != 0:
        row["status"] = "incomplete"
        return False
    run_dir = _discover_campaign_run(row, run_root)
    if run_dir is None and row.get("run_dir"):
        run_dir = Path(row["run_dir"])
    if run_dir is None:
        row["status"] = "invalid"
        return False
    health = _health_for(run_dir)
    if health is None:
        row.update({"status": "invalid", "run_dir": str(run_dir)})
        return False
    row.update({"status": "completed" if health["health_flag"] in {"healthy", "healthy_recovered"} else "incomplete", "run_dir": str(run_dir), "health": health["health_flag"]})
    return _accepted(row)


def run_gate(
    manifest: dict[str, Any],
    gate: str,
    *,
    max_new_pairs: int | None = None,
    confirm_real: bool = False,
    mock: bool = False,
    manifest_file: str | Path | None = None,
    run_root: str | Path | None = None,
    executor: Callable[[list[str]], int] | None = None,
) -> int:
    """Run one explicitly selected gate, sequentially, or simulate it offline."""
    if gate not in {GATE_1, GATE_2}:
        raise ValueError("only replication gates can be executed")
    definition = manifest.get("gates", {}).get(gate, {})
    if definition.get("status") not in {"planned", "approved", "running", "in_progress"}:
        raise ValueError(f"gate {gate} is not unlocked (status={definition.get('status')!r})")
    if not mock and not confirm_real:
        raise ValueError("real gate execution requires --confirm-real")
    _reconcile_rows(manifest, gate)
    if gate == GATE_1:
        hard_budget = float(definition.get("hard_budget_usd", GATE_1_HARD_BUDGET_USD))
    else:
        hard_budget = float(definition.get("approved_budget_usd")) if definition.get("approved_budget_usd") is not None else None
    selected_seeds = _select_pending_pairs(manifest, gate, max_new_pairs)
    root = _resolve(run_root or RUN_ROOT_RELATIVE)
    for seed in selected_seeds:
        pair = _pair_rows(manifest, gate)[seed]
        for condition in ("private", "shared"):
            row = pair.get(condition)
            if row is None:
                raise ValueError(f"paired gate {gate} seed {seed} lacks {condition}")
            if not _run_one_row(row, mock=mock, run_root=root, executor=executor):
                manifest.setdefault("state", {}).update({"status": "gate_incomplete", "active_gate": gate})
                _refresh_cost(manifest, gate)
                _json_write(_manifest_file(manifest, manifest_file), manifest)
                return 1
            _refresh_cost(manifest, gate)
            if hard_budget is not None and float(manifest["gates"][gate].get("observed_cost_usd", 0.0)) >= hard_budget:
                manifest.setdefault("state", {}).update({"status": "stopped_gate_budget", "active_gate": gate})
                _json_write(_manifest_file(manifest, manifest_file), manifest)
                return 2
        manifest.setdefault("state", {})["completed_runs"] = sum(_accepted(item) for item in manifest["runs"])
        manifest["state"]["active_gate"] = gate
        _json_write(_manifest_file(manifest, manifest_file), manifest)
    _reconcile_rows(manifest, gate)
    pair_health = _pair_health(manifest, gate)
    definition["status"] = "complete" if not pair_health["incomplete_pairs"] else "in_progress"
    manifest.setdefault("state", {}).update({"status": "gate_complete" if definition["status"] == "complete" else "gate_in_progress", "active_gate": gate})
    _refresh_cost(manifest, gate)
    _json_write(_manifest_file(manifest, manifest_file), manifest)
    return 0


def approve_gate(
    manifest: dict[str, Any],
    gate: str,
    budget_usd: float,
    *,
    manifest_file: str | Path | None = None,
    report_dir: str | Path | None = None,
) -> None:
    if gate != GATE_2:
        raise ValueError("only Gate 2 requires this approval flow")
    report_root = _resolve(report_dir or (REPORT_ROOT_RELATIVE / "gate-1"))
    summary_path = report_root / "interim_summary.json"
    if not summary_path.exists():
        raise ValueError("Gate 2 approval requires an offline Gate 1 interim report")
    summary_hash = _sha256(summary_path)
    gate1 = manifest["gates"][GATE_1]
    if gate1.get("status") != "complete":
        raise ValueError("Gate 2 approval requires Gate 1 to have complete paired runs")
    if budget_usd <= 0:
        raise ValueError("approved budget must be positive")
    manifest["gates"][GATE_2].update({"status": "approved", "approved_budget_usd": float(budget_usd), "approval": {"gate": gate, "timestamp_utc": datetime.now(UTC).isoformat(), "previous_report_sha256": summary_hash, "git_commit": git_commit()}})
    for row in manifest["runs"]:
        if row.get("gate") == GATE_2 and row.get("status") == "locked":
            row["status"] = "planned"
    manifest["state"].update({"status": "gate_2_approved", "active_gate": GATE_2})
    _json_write(_manifest_file(manifest, manifest_file), manifest)


def _gate_rows_for_report(manifest: dict[str, Any], gate: str) -> list[dict[str, Any]]:
    rows = _rows_for_gate(manifest, gate)
    return [row for row in rows if _accepted(row) and row.get("run_dir")]


def generate_gate_report(manifest: dict[str, Any], gate: str = GATE_1, *, output_dir: str | Path | None = None) -> Path:
    if gate != GATE_1:
        raise ValueError("interim report is currently defined for Gate 1")
    _reconcile_rows(manifest, gate)
    rows = _gate_rows_for_report(manifest, gate)
    pair_health = _pair_health(manifest, gate)
    health_rows: list[dict[str, Any]] = []
    bundles = []
    for row in rows:
        health = _health_for(Path(row["run_dir"]))
        if health:
            health_rows.append({"seed": row["seed"], "condition": row["condition"], "run_id": health["run_id"], **health})
        try:
            bundles.append(load_run(row["run_dir"]))
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            pass
    by_seed: dict[int, dict[str, list[dict[str, Any]]]] = {}
    trajectory_rows: list[dict[str, Any]] = []
    for bundle in bundles:
        by_seed.setdefault(int(bundle.seed or -1), {})[bundle.condition] = hse_trajectory_rows(bundle)
        for checkpoint in checkpoint_rows(bundle):
            trajectory_rows.append({"seed": bundle.seed, "condition": bundle.condition, **checkpoint})
    paired_terminal: list[dict[str, Any]] = []
    for seed, conditions in sorted(by_seed.items()):
        private = conditions.get("private", [])
        shared = conditions.get("shared", [])
        if not private or not shared:
            continue
        p_final, s_final = private[-1], shared[-1]
        paired_terminal.append({
            "seed": seed,
            "delta_hse_private": p_final.get("delta_normalized_hse"),
            "delta_hse_shared": s_final.get("delta_normalized_hse"),
            "D_private_minus_shared": (p_final.get("delta_normalized_hse") - s_final.get("delta_normalized_hse")) if all(isinstance(v, (int, float)) for v in (p_final.get("delta_normalized_hse"), s_final.get("delta_normalized_hse"))) else None,
            "phi_private_0": private[0].get("phi"),
            "phi_private_T": p_final.get("phi"),
            "phi_shared_0": shared[0].get("phi"),
            "phi_shared_T": s_final.get("phi"),
            "delta_phi_private": (p_final.get("phi") - private[0].get("phi")) if all(isinstance(v, (int, float)) for v in (p_final.get("phi"), private[0].get("phi"))) else None,
            "delta_phi_shared": (s_final.get("phi") - shared[0].get("phi")) if all(isinstance(v, (int, float)) for v in (s_final.get("phi"), shared[0].get("phi"))) else None,
            "private_final_mi": p_final.get("normalized_task_agent_mutual_information"),
            "shared_final_mi": s_final.get("normalized_task_agent_mutual_information"),
            "private_final_utilization": p_final.get("normalized_utilization_entropy"),
            "shared_final_utilization": s_final.get("normalized_utilization_entropy"),
            "private_final_oracle_gain": p_final.get("oracle_gain"),
            "shared_final_oracle_gain": s_final.get("oracle_gain"),
            "private_final_d_eff": p_final.get("effective_competence_dimensionality"),
            "shared_final_d_eff": s_final.get("effective_competence_dimensionality"),
        })
    complete_pairs = len(pair_health["complete_pair_seeds"])
    data_quality = {
        "planned_paired_seeds": len(_pair_rows(manifest, gate)),
        "completed_paired_seeds": complete_pairs,
        "complete_pair_seeds": pair_health["complete_pair_seeds"],
        "incomplete_pair_seeds": pair_health["incomplete_pair_seeds"],
        "clean_runs": sum(row.get("health_flag") == "healthy" for row in health_rows),
        "recovered_runs": sum(row.get("health_flag") == "healthy_recovered" for row in health_rows),
        "invalid_runs": sum(row.get("health_flag") == "invalid" for row in health_rows),
        "logical_coverage": {row["run_id"]: row["completion_coverage"] for row in health_rows},
        "physical_attempts": sum(row["physical_attempts"] for row in health_rows),
        "retries": sum(row["retries"] for row in health_rows),
        "timeouts": sum(row["timeout_count"] for row in health_rows),
        "parse_failures": sum(row["parse_error_count"] for row in health_rows),
        "observed_cost_usd": sum(float(row.get("observed_cost_usd") or 0.0) for row in health_rows),
        "latency": [row["latency_s"] for row in health_rows],
    }
    summary = {
        "schema_version": 1,
        "watermark": "INTERIM GATE 1 REPORT — DESCRIPTIVE / NOT A SCIENTIFIC CONCLUSION",
        "campaign": CAMPAIGN_ID,
        "gate": gate,
        "data_quality": data_quality,
        "paired_terminal": paired_terminal,
        "trajectory_rows": trajectory_rows,
        "aggregate": aggregate_runs([bundle.run_dir for bundle in bundles]) if bundles else {"runs": [], "checkpoint_summary": [], "paired_delta_hse": []},
        "questions_for_human_review": [
            "How many complete paired seeds show D_private_minus_shared > 0?",
            "Is the effect consistent or seed-dependent?",
            "Does Phi agree qualitatively with HSE?",
            "Is differentiation task-specific, a global winner, a routing monopoly, or noise?",
            "Does task-agent MI exceed its permutation null?",
            "Does routing exploit available competence (eta_route)?",
            "Is oracle gain/complementarity substantial?",
            "Are raw agent labels symmetric across runs?",
            "Do trajectories appear stabilized by t=20?",
            "Would a long-horizon run add information?",
            "Would random routing be the most informative next control?",
            "Would a softer router be more informative?",
            "Is memory capacity a plausible mechanism?",
            "Is shared/private enough to justify Gate 2?",
            "Is any infrastructure failure confounded with condition?",
        ],
    }
    root = _resolve(output_dir or (REPORT_ROOT_RELATIVE / "gate-1"))
    root.mkdir(parents=True, exist_ok=True)
    _json_write(root / "interim_summary.json", summary)
    _json_write(root / "trajectory_data.json", {"rows": trajectory_rows})
    with (root / "paired_terminal.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = sorted({key for row in paired_terminal for key in row}) if paired_terminal else ["seed"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(paired_terminal)
    markdown = [
        "# Data quality",
        "",
        "**INTERIM GATE 1 REPORT — descriptive diagnostics; not a scientific conclusion.**",
        "",
        "| quantity | value |",
        "|---|---:|",
    ]
    for key, value in data_quality.items():
        if isinstance(value, (str, int, float)):
            markdown.append(f"| {key} | {value} |")
    markdown += ["", "# Paired terminal diagnostics", "", "See `paired_terminal.csv` for one row per complete seed.", "", "```json", json.dumps(paired_terminal, indent=2), "```", "", "# Trajectory data", "", "Machine-readable checkpoint rows are in `trajectory_data.json`.", "", "# Questions for human review", ""]
    markdown.extend(f"{index}. {question}" for index, question in enumerate(summary["questions_for_human_review"], start=1))
    markdown += ["", "# Candidate follow-ups", "", "Random routing, softmax routing, locality, memory capacity, long horizon and interventions remain optional candidates. No candidate is unlocked by this report."]
    (root / "INTERIM_REPORT.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    return root / "INTERIM_REPORT.md"


def _print_plan(manifest: dict[str, Any], gate: str | None = None, max_new_pairs: int | None = None) -> None:
    if gate:
        definition = manifest["gates"][gate]
        rows = _rows_for_gate(manifest, gate)
        pending = _select_pending_pairs(manifest, gate, max_new_pairs) if definition.get("status") != "locked" else []
        print(json.dumps({"gate": gate, "definition": definition, "pending_pair_seeds": pending, "runs": rows}, indent=2, sort_keys=True))
        return
    print(json.dumps({key: manifest[key] for key in ("campaign", "protocol_version", "base_commit", "probe_set_hash", "budget_policy", "cost_forecast", "gates", "state")}, indent=2, sort_keys=True))
    print("planned identities:", len(manifest["runs"]))


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Plan/status/report a human-gated developmental-dynamics campaign")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true", help="print full staged plan; never calls a model")
    mode.add_argument("--plan-gate", choices=[GATE_1, GATE_2], help="print one gate plan")
    mode.add_argument("--status", action="store_true", help="show current campaign state")
    mode.add_argument("--cost", action="store_true", help="show offline cost state")
    mode.add_argument("--report-gate", choices=[GATE_1], help="generate an offline interim report")
    mode.add_argument("--approve-gate", choices=[GATE_2], help="record explicit human approval for Gate 2")
    mode.add_argument("--run-gate", choices=[GATE_1, GATE_2], help="execute one gate; requires --confirm-real")
    mode.add_argument("--resume", action="store_true", help="resume the active unlocked gate; requires --confirm-real")
    parser.add_argument("--max-new-pairs", type=int, help="deterministically limit a gate plan/run to pending paired seeds")
    parser.add_argument("--budget-usd", type=float, help="approved budget for --approve-gate")
    parser.add_argument("--confirm-real", action="store_true", help="explicit acknowledgement for real DeepSeek execution")
    parser.add_argument("--mock", action="store_true", help="use MockBackend via --dry-run; only for local tests")
    parser.add_argument("--force-manifest", action="store_true", help="migrate/rebuild only before any gate execution")
    args = parser.parse_args(list(argv) if argv is not None else None)
    manifest = create_manifest(force=args.force_manifest)
    if args.plan_gate:
        _print_plan(manifest, args.plan_gate, args.max_new_pairs)
    elif args.plan or not any((args.status, args.cost, args.report_gate, args.approve_gate, args.run_gate, args.resume)):
        _print_plan(manifest)
    elif args.status:
        print(json.dumps({"state": manifest["state"], "gates": manifest["gates"]}, indent=2, sort_keys=True))
    elif args.cost:
        print(json.dumps({"budget_policy": manifest["budget_policy"], "cost_forecast": manifest["cost_forecast"], "state": manifest["state"]}, indent=2, sort_keys=True))
    elif args.report_gate:
        print(f"Wrote offline interim report: {generate_gate_report(manifest, args.report_gate)}")
    elif args.approve_gate:
        if args.budget_usd is None:
            raise SystemExit("--approve-gate requires --budget-usd")
        approve_gate(manifest, args.approve_gate, args.budget_usd)
        print(f"Approved {args.approve_gate} offline; no inference was executed")
    elif args.run_gate or args.resume:
        gate = args.run_gate or manifest["state"].get("active_gate", GATE_1)
        if not args.mock and not args.confirm_real:
            raise SystemExit("real gate execution requires --confirm-real")
        raise SystemExit(run_gate(manifest, gate, max_new_pairs=args.max_new_pairs, confirm_real=args.confirm_real, mock=args.mock))


if __name__ == "__main__":
    main()
