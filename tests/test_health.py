from __future__ import annotations

import unittest
import json
import tempfile
from pathlib import Path

from emergent_specialization.health import run_health


class HealthTests(unittest.TestCase):
    def test_complete_run_with_recovered_attempt_is_healthy_recovered(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            probe_path = root / "probes.json"
            probe_path.write_text(json.dumps({"tasks": []}), encoding="utf-8")
            run = root / "run"
            run.mkdir()
            (run / "metadata.json").write_text(json.dumps({
                "run_id": "recovered",
                "config": {
                    "experiment": {"num_agents": 2, "num_rounds": 1, "checkpoints": []},
                    "logging": {"probe_set_path": str(probe_path)},
                },
            }), encoding="utf-8")
            events = [
                {"event": "inference", "phase": "round", "round_id": 1, "checkpoint": None,
                 "probe_index": None, "agent_id": "agent_0", "attempt": 0,
                 "error": "rate limit", "latency_s": 0.1, "token_usage": {}},
                {"event": "inference", "phase": "round", "round_id": 1, "checkpoint": None,
                 "probe_index": None, "agent_id": "agent_0", "attempt": 1,
                 "error": None, "latency_s": 0.1, "token_usage": {"prompt_tokens": 1, "completion_tokens": 1}},
                {"event": "inference", "phase": "round", "round_id": 1, "checkpoint": None,
                 "probe_index": None, "agent_id": "agent_1", "attempt": 0,
                 "error": None, "latency_s": 0.1, "token_usage": {"prompt_tokens": 1, "completion_tokens": 1}},
            ]
            (run / "events.jsonl").write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")
            (run / "metrics.jsonl").write_text("", encoding="utf-8")
            (run / "summary.json").write_text(json.dumps({"run_id": "recovered", "status": "completed"}), encoding="utf-8")
            health = run_health(run)
            self.assertEqual(health["health_flag"], "healthy_recovered")
            self.assertEqual(health["health_classification"], "HEALTHY / RECOVERED")

    def test_existing_private_run_is_flagged_invalid_when_logical_calls_are_missing(self) -> None:
        root = Path(__file__).resolve().parents[1]
        run_dir = root / "data" / "runs" / "private-seed1-20260806T231032Z-ff928a0b"
        if not run_dir.exists():
            self.skipTest("recorded real runs are not present")
        health = run_health(run_dir)
        self.assertEqual(health["expected_logical_completions"], 400)
        self.assertEqual(health["successful_logical_completions"], 398)
        self.assertEqual(health["health_flag"], "invalid")

    def test_incomplete_failed_run_is_auditable_without_checkpoint_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            probe_path = root / "probes.json"
            probe_path.write_text(json.dumps({"tasks": [{"world": "ALPHA"}]}), encoding="utf-8")
            run = root / "run"
            run.mkdir()
            (run / "metadata.json").write_text(json.dumps({
                "run_id": "failed",
                "config": {
                    "experiment": {"num_agents": 2, "num_rounds": 3, "checkpoints": [0, 2, 3]},
                    "logging": {"probe_set_path": str(probe_path)},
                },
            }), encoding="utf-8")
            (run / "events.jsonl").write_text("", encoding="utf-8")
            (run / "metrics.jsonl").write_text("", encoding="utf-8")
            (run / "summary.json").write_text(json.dumps({"run_id": "failed", "status": "failed"}), encoding="utf-8")
            health = run_health(run)
            self.assertEqual(health["expected_logical_completions"], 12)
            self.assertEqual(health["missing_logical_completions"], 12)
            self.assertEqual(health["health_flag"], "invalid")
