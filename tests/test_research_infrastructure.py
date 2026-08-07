from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from emergent_specialization.aggregate import aggregate_runs
from emergent_specialization.batch import nominal_call_counts, plan_batch
from emergent_specialization.config import (
    AgentSettings,
    ConditionSettings,
    ExperimentSettings,
    FeedbackSettings,
    LoggingSettings,
    RunConfig,
    load_config,
    normalize_checkpoints,
)
from emergent_specialization.environment import HiddenWorldEnvironment
from emergent_specialization.experiment import ExperimentRunner
from emergent_specialization.metrics.information import mi_null_diagnostic
from emergent_specialization.metrics.online import online_observables
from emergent_specialization.metrics.permutation import (
    align_competence_profiles,
    ensemble_symmetry_within_run_asymmetry,
    within_run_asymmetry,
)
from emergent_specialization.probes import generate_probe_payload, write_probe_set
from emergent_specialization.providers.mock import MockBackend


class CheckpointAndFeedbackTests(unittest.TestCase):
    def test_checkpoint_schedule_includes_start_and_final(self) -> None:
        self.assertEqual(normalize_checkpoints({"every": 5}, 12), (0, 5, 10, 12))
        self.assertEqual(normalize_checkpoints([], 12), ())
        with self.assertRaises(ValueError):
            normalize_checkpoints({"every": 0}, 12)
        with self.assertRaises(ValueError):
            normalize_checkpoints([0, 0], 12)
        with self.assertRaises(ValueError):
            ExperimentSettings(num_rounds=4, checkpoints=(0, 5))

    def test_legacy_configs_keep_their_feedback_policy(self) -> None:
        root = Path(__file__).resolve().parents[1]
        private = load_config(root / "configs" / "pilot_private.yaml")
        shared = load_config(root / "configs" / "pilot_shared.yaml")
        self.assertEqual(private.effective_feedback.mode, "private")
        self.assertEqual(shared.effective_feedback.mode, "shared")
        self.assertEqual(FeedbackSettings("probabilistic", 1.0).as_label(), "probabilistic-p1")

    def test_probabilistic_endpoints_are_exact(self) -> None:
        self.assertEqual(FeedbackSettings("probabilistic", 0.0).mode, "probabilistic")
        self.assertEqual(FeedbackSettings("probabilistic", 1.0).private_probability, 1.0)

    def _run(self, feedback: FeedbackSettings) -> ExperimentRunner:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        probes = root / "probes.json"
        write_probe_set(probes, generate_probe_payload(HiddenWorldEnvironment(), per_world=1))
        config = RunConfig(
            experiment=ExperimentSettings(num_agents=4, num_rounds=2, checkpoints=(), technical_retries=0, console_summary=False),
            agent=AgentSettings(backend="mock"),
            condition=ConditionSettings(memory_mode="private"),
            feedback=feedback,
            logging=LoggingSettings(output_dir=str(root / "runs"), probe_set_path=str(probes)),
        )
        runner = ExperimentRunner(config, backend=MockBackend())
        asyncio.run(runner.run())
        return runner

    def test_probabilistic_one_and_zero_match_private_and_shared_memory_counts(self) -> None:
        private = self._run(FeedbackSettings("probabilistic", 1.0))
        shared = self._run(FeedbackSettings("probabilistic", 0.0))
        self.assertEqual(sum(len(agent.memory) for agent in private.agents), 2)
        self.assertEqual([len(agent.memory) for agent in shared.agents], [2, 2, 2, 2])


class OnlineAndBatchTests(unittest.TestCase):
    def test_online_observables_are_cumulative_and_probe_free(self) -> None:
        events = [
            {
                "event": "round_complete", "round": 1,
                "task": {"world": "ALPHA"}, "selected_agent_id": "agent_0",
                "selected_correct": True, "feedback_recipients": ["agent_0"],
                "candidates": {"agent_0": {"confidence": 0.8}, "agent_1": {"confidence": 0.2}},
            },
            {
                "event": "round_complete", "round": 2,
                "task": {"world": "BETA"}, "selected_agent_id": "agent_1",
                "selected_correct": False, "feedback_recipients": ["agent_1"],
                "candidates": {"agent_0": {"confidence": 0.3}, "agent_1": {"confidence": 0.7}},
            },
            {"event": "inference", "phase": "probe"},
        ]
        rows = online_observables(events, num_agents=2)
        self.assertEqual([row["round"] for row in rows], [1, 2])
        self.assertEqual(rows[-1]["memory_counts"], {"agent_0": 1, "agent_1": 1})
        self.assertAlmostEqual(rows[-1]["cumulative_accuracy"], 0.5)
        self.assertEqual(rows[-1]["routing_concentration"], 0.5)

    def test_batch_plan_counts_nominal_and_retry_ceiling(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = load_config(root / "configs" / "pilot_private.yaml")
        counts = nominal_call_counts(config, 40)
        self.assertEqual(counts["nominal_calls"], 400)
        self.assertEqual(counts["max_physical_calls"], 800)

    def test_batch_plan_expands_seed_and_condition_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            probes = root / "probes.json"
            write_probe_set(probes, generate_probe_payload(HiddenWorldEnvironment(), per_world=1))
            config = root / "private.yaml"
            config.write_text(
                "experiment:\n  num_agents: 2\n  num_rounds: 3\n  checkpoints: {every: 2}\n  technical_retries: 0\n"
                "agent:\n  backend: mock\ncondition:\n  memory_mode: private\n"
                f"logging:\n  output_dir: {root / 'runs'}\n  probe_set_path: {probes}\n",
                encoding="utf-8",
            )
            batch = root / "batch.yaml"
            batch.write_text(f"seeds: [1, 2]\nconfigs: [{config}]\noutput_dir: {root / 'runs'}\n", encoding="utf-8")
            rows = plan_batch(batch)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0].nominal_calls, 2 * 3 + 3 * 4 * 2)


class PermutationAndMIDiagnosticsTests(unittest.TestCase):
    def test_alignment_ignores_agent_labels(self) -> None:
        reference = {"agent_0": {"ALPHA": 1.0, "BETA": 0.0}, "agent_1": {"ALPHA": 0.0, "BETA": 1.0}}
        candidate = {"agent_x": {"ALPHA": 0.0, "BETA": 1.0}, "agent_y": {"ALPHA": 1.0, "BETA": 0.0}}
        mapping, cost = align_competence_profiles(reference, candidate)
        self.assertEqual(cost, 0.0)
        self.assertEqual(mapping, {"agent_x": "agent_1", "agent_y": "agent_0"})
        self.assertGreater(within_run_asymmetry(reference), 0.0)

    def test_ensemble_summary_exposes_both_levels(self) -> None:
        run = {"a": {"ALPHA": 1.0, "BETA": 0.0}, "b": {"ALPHA": 0.0, "BETA": 1.0}}
        summary = ensemble_symmetry_within_run_asymmetry([run, run])
        self.assertGreater(summary["mean_within_run_asymmetry"], 0.0)
        self.assertGreaterEqual(summary["label_usage_entropy"], 0.0)

    def test_mi_null_is_seeded_and_explicitly_diagnostic(self) -> None:
        first = mi_null_diagnostic(["A", "A", "B", "B"], ["x", "x", "y", "y"], permutations=20, seed=4)
        second = mi_null_diagnostic(["A", "A", "B", "B"], ["x", "x", "y", "y"], permutations=20, seed=4)
        self.assertEqual(first, second)
        self.assertIn("excess_mi", first)
