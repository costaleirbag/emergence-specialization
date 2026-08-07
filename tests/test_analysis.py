from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from emergent_specialization.analysis import (
    behavioral_rows,
    candidate_rows,
    checkpoint_rows,
    competence_rows,
    load_run,
    memory_rows,
    overview_record,
    round_rows,
    usage_summary,
)
from emergent_specialization.config import (
    AgentSettings,
    ConditionSettings,
    ExperimentSettings,
    LoggingSettings,
    RunConfig,
)
from emergent_specialization.environment import HiddenWorldEnvironment
from emergent_specialization.experiment import ExperimentRunner
from emergent_specialization.probes import generate_probe_payload, write_probe_set
from emergent_specialization.providers.mock import MockBackend


class AnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        probes = root / "probes.json"
        write_probe_set(probes, generate_probe_payload(HiddenWorldEnvironment(), per_world=1))
        config = RunConfig(
            experiment=ExperimentSettings(
                num_agents=4,
                num_rounds=2,
                checkpoints=(0, 2),
                max_concurrency=8,
                technical_retries=0,
                console_summary=False,
            ),
            agent=AgentSettings(backend="mock", memory_k=3),
            condition=ConditionSettings(memory_mode="private"),
            logging=LoggingSettings(output_dir=str(root / "runs"), probe_set_path=str(probes)),
        )
        self.run_dir = asyncio.run(ExperimentRunner(config, backend=MockBackend()).run())
        self.bundle = load_run(self.run_dir)

    def test_loads_completed_run_with_hashes_and_provenance(self) -> None:
        self.assertEqual(self.bundle.condition, "private")
        self.assertEqual(self.bundle.backend_name, "mock")
        self.assertTrue(self.bundle.is_mock)
        self.assertEqual(set(self.bundle.input_hashes), {"metadata.json", "events.jsonl", "metrics.jsonl", "summary.json"})
        self.assertEqual(overview_record(self.bundle)["rounds"], 2)
        self.assertEqual(usage_summary(self.bundle)["status"], "unavailable")

    def test_normalized_analysis_tables_have_expected_shapes(self) -> None:
        self.assertEqual(len(round_rows(self.bundle)), 2)
        self.assertEqual(len(candidate_rows(self.bundle)), 8)
        self.assertEqual(len(checkpoint_rows(self.bundle)), 2)
        self.assertEqual(len(competence_rows(self.bundle)), 2 * 4 * 4)
        self.assertEqual(len(behavioral_rows(self.bundle)), 2 * 4 * 4)
        self.assertEqual(len(memory_rows(self.bundle)), 3 * 4)

    def test_checkpoint_rows_expose_analysis_only_differentiation_fields(self) -> None:
        rows = checkpoint_rows(self.bundle)
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertIn("phi", row)
            self.assertIn("routing_alignment_eta", row)
            self.assertIn("division_of_labor_match", row)
