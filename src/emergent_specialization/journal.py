"""SQLite execution journal for resumable logical completions.

The journal is an operational cache/state machine. JSONL artifacts remain the
human-facing scientific record and are never replaced by SQL queries.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


def _json(value: Any) -> str:
    if is_dataclass(value):
        value = asdict(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


class ExecutionJournal:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS run_state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS physical_attempts (
                logical_id TEXT NOT NULL,
                attempt INTEGER NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY (logical_id, attempt)
            );
            CREATE TABLE IF NOT EXISTS logical_completions (
                logical_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS round_commits (
                round_id INTEGER PRIMARY KEY,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS checkpoint_snapshots (
                checkpoint INTEGER PRIMARY KEY,
                snapshot_hash TEXT NOT NULL,
                memory_json TEXT NOT NULL
            );
            """
        )

    def close(self) -> None:
        self.connection.commit()
        self.connection.close()

    def set_state(self, key: str, value: Any) -> None:
        self.connection.execute(
            "INSERT INTO run_state(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, _json(value)),
        )

    def get_state(self, key: str, default: Any = None) -> Any:
        row = self.connection.execute("SELECT value FROM run_state WHERE key=?", (key,)).fetchone()
        return default if row is None else json.loads(row[0])

    def record_attempt(self, logical_id: str, attempt: int, payload: Any) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO physical_attempts(logical_id, attempt, payload) VALUES(?, ?, ?)",
            (logical_id, attempt, _json(payload)),
        )

    def record_logical_completion(self, logical_id: str, payload: Any) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO logical_completions(logical_id, payload) VALUES(?, ?)",
            (logical_id, _json(payload)),
        )

    def completed(self, logical_id: str) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT payload FROM logical_completions WHERE logical_id=?", (logical_id,)).fetchone()
        return None if row is None else json.loads(row[0])

    def record_round_commit(self, round_id: int, payload: Any) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO round_commits(round_id, payload) VALUES(?, ?)",
            (round_id, _json(payload)),
        )

    def round_committed(self, round_id: int) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT payload FROM round_commits WHERE round_id=?", (round_id,)).fetchone()
        return None if row is None else json.loads(row[0])

    def record_snapshot(self, checkpoint: int, snapshot_hash: str, memory: Any) -> None:
        self.connection.execute(
            "INSERT INTO checkpoint_snapshots(checkpoint, snapshot_hash, memory_json) VALUES(?, ?, ?) "
            "ON CONFLICT(checkpoint) DO UPDATE SET snapshot_hash=excluded.snapshot_hash, memory_json=excluded.memory_json",
            (checkpoint, snapshot_hash, _json(memory)),
        )

    def snapshot(self, checkpoint: int) -> tuple[str, Any] | None:
        row = self.connection.execute(
            "SELECT snapshot_hash, memory_json FROM checkpoint_snapshots WHERE checkpoint=?", (checkpoint,)
        ).fetchone()
        return None if row is None else (str(row[0]), json.loads(row[1]))

    def physical_attempts(self) -> int:
        row = self.connection.execute("SELECT COUNT(*) FROM physical_attempts").fetchone()
        return int(row[0]) if row else 0

    def completed_count(self) -> int:
        row = self.connection.execute("SELECT COUNT(*) FROM logical_completions").fetchone()
        return int(row[0]) if row else 0

    def attempt_payloads(self) -> list[dict[str, Any]]:
        rows = self.connection.execute("SELECT payload FROM physical_attempts ORDER BY logical_id, attempt").fetchall()
        return [json.loads(row[0]) for row in rows]
