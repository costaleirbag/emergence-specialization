from __future__ import annotations

import unittest
from pathlib import Path

from emergent_specialization.health import run_health


class HealthTests(unittest.TestCase):
    def test_existing_private_run_is_flagged_invalid_when_logical_calls_are_missing(self) -> None:
        root = Path(__file__).resolve().parents[1]
        run_dir = root / "data" / "runs" / "private-seed1-20260806T231032Z-ff928a0b"
        if not run_dir.exists():
            self.skipTest("recorded real runs are not present")
        health = run_health(run_dir)
        self.assertEqual(health["expected_logical_completions"], 400)
        self.assertEqual(health["successful_logical_completions"], 398)
        self.assertEqual(health["health_flag"], "invalid")
