"""Append-only JSONL logging for raw calls and derived metrics."""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any


def _json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Not JSON serializable: {type(value).__name__}")


def json_line(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, default=_json_default, ensure_ascii=False)


def git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], text=True, capture_output=True, check=False, timeout=3
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def installed_versions() -> dict[str, str]:
    versions = {"python": sys.version, "platform": platform.platform()}
    for package in ("PyYAML", "emergent-specialization"):
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = "not-installed"
    return versions


class RunLogger:
    def __init__(self, base_dir: str | Path, run_id: str) -> None:
        self.run_id = run_id
        self.run_dir = Path(base_dir) / run_id
        self.run_dir.mkdir(parents=True, exist_ok=False)
        self.events_path = self.run_dir / "events.jsonl"
        self.metrics_path = self.run_dir / "metrics.jsonl"

    def write_metadata(self, metadata_payload: dict[str, Any]) -> None:
        payload = {
            "run_id": self.run_id,
            "created_at_utc": datetime.now(UTC).isoformat(),
            "git_commit": git_commit(),
            "runtime": installed_versions(),
            **metadata_payload,
        }
        (self.run_dir / "metadata.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8"
        )

    def event(self, event_type: str, payload: dict[str, Any]) -> None:
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json_line({"event": event_type, **payload}) + "\n")

    def metrics(self, payload: dict[str, Any]) -> None:
        with self.metrics_path.open("a", encoding="utf-8") as handle:
            handle.write(json_line(payload) + "\n")

    def write_summary(self, payload: dict[str, Any]) -> None:
        (self.run_dir / "summary.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8"
        )
