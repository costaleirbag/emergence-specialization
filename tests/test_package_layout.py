from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PackageLayoutTests(unittest.TestCase):
    def test_legacy_launcher_targets_the_relocated_runtime(self) -> None:
        launcher = (ROOT / "scripts" / "run-deepseek-experiment.sh").read_text(encoding="utf-8")
        self.assertIn("emergent_specialization.runtime.experiment", launcher)
        self.assertNotIn("emergent_specialization.experiment", launcher)

    def test_report_entrypoint_is_a_real_module(self) -> None:
        from emergent_specialization.reporting.notebooks import generate_run_report

        self.assertTrue(callable(generate_run_report))

    def test_mock_readiness_uses_relocated_modules(self) -> None:
        source = (ROOT / "scripts" / "generate_mock_readiness.py").read_text(encoding="utf-8")
        for module in (
            "emergent_specialization.reporting.analysis",
            "emergent_specialization.core.config",
            "emergent_specialization.core.environment",
            "emergent_specialization.runtime.experiment",
            "emergent_specialization.core.probes",
        ):
            self.assertIn(module, source)
        self.assertNotIn("from emergent_specialization.analysis", source)
        self.assertNotIn("from emergent_specialization.experiment", source)
