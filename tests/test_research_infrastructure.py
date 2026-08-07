from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from emergent_specialization.aggregate import aggregate_runs
from emergent_specialization.batch import nominal_call_counts, plan_batch, plan_manifest, run_batch
from emergent_specialization.config import (
    AgentSettings,
    ConditionSettings,
    ExperimentSettings,
    FeedbackSettings,
    InitialConditionSettings,
    LoggingSettings,
    RunConfig,
    load_config,
    normalize_checkpoints,
)
from emergent_specialization.environment import HiddenWorldEnvironment
from emergent_specialization.experiment import ExperimentRunner
from emergent_specialization.interventions import (
    InterventionSpec,
    PopulationState,
    apply_memory_intervention,
    apply_population_intervention,
)
from emergent_specialization.agents import ExperimentalAgent
from emergent_specialization.models import Experience
from emergent_specialization.metrics.information import mi_null_diagnostic
from emergent_specialization.metrics.online import online_observables
from emergent_specialization.metrics.permutation import (
    align_competence_profiles,
    argmax_label_counts,
    ensemble_symmetry_within_run_asymmetry,
    world_argmax_label_counts,
    within_run_asymmetry,
)
from emergent_specialization.probes import generate_probe_payload, write_probe_set
from emergent_specialization.providers.mock import MockBackend
from emergent_specialization.models import BackendResponse


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

    def test_yaml_feedback_schedule_is_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scheduled.yaml"
            path.write_text(
                "experiment:\n  num_rounds: 4\n  checkpoints: {every: 2}\n"
                "feedback:\n  mode: probabilistic\n  private_probability: 0.2\n  schedule: [[3, 0.8]]\n",
                encoding="utf-8",
            )
            config = load_config(path)
            self.assertEqual(config.experiment.checkpoints, (0, 2, 4))
            self.assertEqual(config.effective_feedback.schedule, ((3, 0.8),))

    def test_probabilistic_endpoints_are_exact(self) -> None:
        self.assertEqual(FeedbackSettings("probabilistic", 0.0).mode, "probabilistic")
        self.assertEqual(FeedbackSettings("probabilistic", 1.0).private_probability, 1.0)
        scheduled = FeedbackSettings("probabilistic", 0.2, ((3, 0.8),))
        self.assertAlmostEqual(scheduled.probability_at(2), 0.2)
        self.assertAlmostEqual(scheduled.probability_at(3), 0.8)

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

    def test_legacy_private_shared_pair_keeps_task_sequence_identical(self) -> None:
        def execute(mode: str) -> list[dict[str, object]]:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                probes = root / "probes.json"
                write_probe_set(probes, generate_probe_payload(HiddenWorldEnvironment(), per_world=1))
                config = RunConfig(
                    experiment=ExperimentSettings(
                        num_agents=4, num_rounds=4, checkpoints=(), seed=11,
                        task_seed=31, router_seed=41, technical_retries=0, console_summary=False,
                    ),
                    agent=AgentSettings(backend="mock"),
                    condition=ConditionSettings(memory_mode=mode),
                    logging=LoggingSettings(output_dir=str(root / "runs"), probe_set_path=str(probes)),
                )
                run_dir = asyncio.run(ExperimentRunner(config, backend=MockBackend()).run())
                return [
                    json.loads(line)
                    for line in (run_dir / "events.jsonl").read_text().splitlines()
                    if json.loads(line).get("event") == "round_complete"
                ]

        private = execute("private")
        shared = execute("shared")
        self.assertEqual([event["task"] for event in private], [event["task"] for event in shared])


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

    def test_online_mi_null_is_opt_in_after_minimum_sample(self) -> None:
        events = []
        for index in range(8):
            events.append(
                {
                    "event": "round_complete", "round": index + 1,
                    "task": {"world": "ALPHA" if index < 4 else "BETA"},
                    "selected_agent_id": "agent_0" if index % 2 == 0 else "agent_1",
                    "selected_correct": True, "feedback_recipients": ["agent_0"],
                    "candidates": {"agent_0": {"confidence": 0.8}, "agent_1": {"confidence": 0.2}},
                }
            )
        rows = online_observables(events, num_agents=2, mi_permutations=10, mi_min_samples=8)
        self.assertNotIn("mi_null_diagnostic", rows[0])
        self.assertIn("mi_null_diagnostic", rows[-1])

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

    def test_batch_manifest_contains_reproducibility_fields_and_run_requires_confirmation(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = root / "configs" / "research" / "replication_private.yaml"
        batch = root / "configs" / "research" / "batches" / "private_shared_replication_5seeds.yaml"
        rows = plan_batch(batch)
        manifest = plan_manifest(batch, rows)
        self.assertEqual(len(manifest["runs"]), 10)
        self.assertIn("git_commit", manifest)
        self.assertIn("system_prompt_hash", manifest["runs"][0])
        with self.assertRaises(ValueError):
            run_batch(rows[:1], output_root=root / "data" / "runs" / "replication")

    def test_direct_replication_plan_uses_nominal_560_and_hard_700_ceiling(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = load_config(root / "configs" / "research" / "replication_private.yaml")
        counts = nominal_call_counts(config, 40)
        self.assertEqual(counts["nominal_calls"], 560)
        self.assertEqual(counts["max_physical_calls"], 700)

    def test_mock_paired_seed_has_expected_artifacts_and_different_feedback_recipients(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            probes = root / "probes.json"
            write_probe_set(probes, generate_probe_payload(HiddenWorldEnvironment(), per_world=1))

            def execute(condition: str) -> tuple[Path, list[dict[str, object]]]:
                config = RunConfig(
                    experiment=ExperimentSettings(
                        num_agents=2, num_rounds=3, checkpoints=(0, 2, 3), seed=1,
                        technical_retries=0, console_summary=False,
                    ),
                    agent=AgentSettings(backend="mock"),
                    condition=ConditionSettings(memory_mode=condition),
                    logging=LoggingSettings(output_dir=str(root / "runs" / condition), probe_set_path=str(probes)),
                )
                run_dir = asyncio.run(ExperimentRunner(config, backend=MockBackend()).run())
                events = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]
                return run_dir, [event for event in events if event["event"] == "round_complete"]

            private_dir, private_rounds = execute("private")
            shared_dir, shared_rounds = execute("shared")
            self.assertEqual([event["task"] for event in private_rounds], [event["task"] for event in shared_rounds])
            self.assertTrue(all(len(event["feedback_recipients"]) == 1 for event in private_rounds))
            self.assertTrue(all(len(event["feedback_recipients"]) == 2 for event in shared_rounds))
            for run_dir in (private_dir, shared_dir):
                for filename in ("metadata.json", "events.jsonl", "metrics.jsonl", "summary.json"):
                    self.assertTrue((run_dir / filename).is_file())

    def test_resume_reuses_completed_logical_interaction_and_is_idempotent(self) -> None:
        class FailFirstBackend(MockBackend):
            def __init__(self) -> None:
                self.calls = 0

            async def complete(self, **kwargs: object) -> BackendResponse:
                self.calls += 1
                if self.calls == 1:
                    return BackendResponse(raw_response=None, latency_s=0.0, error="synthetic failure", retryable=False)
                return await super().complete(**kwargs)  # type: ignore[arg-type]

        class CountingBackend(MockBackend):
            def __init__(self) -> None:
                self.calls = 0

            async def complete(self, **kwargs: object) -> BackendResponse:
                self.calls += 1
                return await super().complete(**kwargs)  # type: ignore[arg-type]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            probes = root / "probes.json"
            write_probe_set(probes, generate_probe_payload(HiddenWorldEnvironment(), per_world=1))
            config = RunConfig(
                experiment=ExperimentSettings(num_agents=2, num_rounds=1, checkpoints=(), technical_retries=0, console_summary=False),
                agent=AgentSettings(backend="mock"),
                condition=ConditionSettings(memory_mode="private"),
                logging=LoggingSettings(output_dir=str(root / "runs"), probe_set_path=str(probes)),
            )
            first = FailFirstBackend()
            with self.assertRaises(RuntimeError):
                asyncio.run(ExperimentRunner(config, backend=first).run())
            run_dir = next((root / "runs").iterdir())
            recovery = CountingBackend()
            asyncio.run(ExperimentRunner(config, backend=recovery, resume_dir=run_dir).run())
            self.assertEqual(recovery.calls, 1)
            repeated = CountingBackend()
            asyncio.run(ExperimentRunner(config, backend=repeated, resume_dir=run_dir).run())
            self.assertEqual(repeated.calls, 0)

    def test_retryable_physical_attempt_is_recorded_and_recovered(self) -> None:
        class RetryOnceBackend(MockBackend):
            def __init__(self) -> None:
                self.calls = 0

            async def complete(self, **kwargs: object) -> BackendResponse:
                self.calls += 1
                if self.calls == 1:
                    return BackendResponse(
                        raw_response=None,
                        latency_s=0.0,
                        error="synthetic rate limit",
                        error_category="rate_limit",
                        retryable=True,
                        http_status=429,
                        retry_after_s=0.0,
                    )
                return await super().complete(**kwargs)  # type: ignore[arg-type]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            probes = root / "probes.json"
            write_probe_set(probes, generate_probe_payload(HiddenWorldEnvironment(), per_world=1))
            config = RunConfig(
                experiment=ExperimentSettings(
                    num_agents=2, num_rounds=1, checkpoints=(), technical_retries=1,
                    console_summary=False,
                ),
                agent=AgentSettings(backend="mock"),
                condition=ConditionSettings(memory_mode="private"),
                logging=LoggingSettings(output_dir=str(root / "runs"), probe_set_path=str(probes)),
            )
            backend = RetryOnceBackend()
            run_dir = asyncio.run(ExperimentRunner(config, backend=backend).run())
            events = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]
            attempts = [event for event in events if event["event"] == "inference"]
            self.assertEqual(len(attempts), 3)
            self.assertEqual(sum(event.get("attempt", 0) for event in attempts), 1)

    def test_aggregate_exposes_paired_delta_hse_field(self) -> None:
        root = Path(__file__).resolve().parents[1]
        private = root / "data" / "runs" / "private-seed1-20260806T231032Z-ff928a0b"
        shared = root / "data" / "runs" / "shared-seed1-20260807T002355Z-557768c8"
        if not private.exists() or not shared.exists():
            self.skipTest("recorded real runs are not present")
        result = aggregate_runs([private, shared])
        self.assertEqual(len(result["paired_delta_hse"]), 2)
        self.assertIn("paired_difference_right_minus_left", result["paired_delta_hse"][0])


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

    def test_raw_label_argmax_counts_are_available_as_exchangeability_sanity_checks(self) -> None:
        self.assertEqual(argmax_label_counts([{"agent_0": 2, "agent_1": 1}, {"agent_1": 3, "agent_0": 1}]), {"agent_0": 1, "agent_1": 1})
        profiles = [
            {"agent_0": {"ALPHA": 1.0}, "agent_1": {"ALPHA": 0.0}},
            {"agent_0": {"ALPHA": 0.0}, "agent_1": {"ALPHA": 1.0}},
        ]
        self.assertEqual(world_argmax_label_counts(profiles)["ALPHA"], {"agent_0": 1, "agent_1": 1})

    def test_mi_null_is_seeded_and_explicitly_diagnostic(self) -> None:
        first = mi_null_diagnostic(["A", "A", "B", "B"], ["x", "x", "y", "y"], permutations=20, seed=4)
        second = mi_null_diagnostic(["A", "A", "B", "B"], ["x", "x", "y", "y"], permutations=20, seed=4)
        self.assertEqual(first, second)
        self.assertIn("excess_mi", first)


class InterventionTests(unittest.TestCase):
    def _experience(self, round_id: int, world: str = "ALPHA") -> Experience:
        return Experience(round_id, world, round_id, 1, 2, 0.7, 3, True)

    def test_memory_swap_erase_and_clone_are_auditable(self) -> None:
        left = ExperimentalAgent("agent_0", [self._experience(1), self._experience(2, "BETA")])
        right = ExperimentalAgent("agent_1", [self._experience(3)])
        payload = apply_memory_intervention(
            [left, right], InterventionSpec(1, "memory_swap", "agent_0", "agent_1")
        )
        self.assertEqual([item.round_id for item in left.memory], [3])
        self.assertEqual([item.round_id for item in right.memory], [1, 2])
        self.assertEqual(len(payload["before"]), 2)
        apply_memory_intervention([left, right], InterventionSpec(2, "memory_clone", "agent_1", "agent_0"))
        self.assertEqual([item.round_id for item in left.memory], [1, 2])
        apply_memory_intervention([left, right], InterventionSpec(3, "memory_erase", target_agent="agent_0"))
        self.assertEqual(left.memory, [])

    def test_population_state_keeps_removed_memory_separate(self) -> None:
        original = ExperimentalAgent("agent_0", [self._experience(1)])
        state = PopulationState({"agent_0": original})
        apply_population_intervention(state, InterventionSpec(1, "ablate_agent", target_agent="agent_0"))
        self.assertNotIn("agent_0", state.active)
        self.assertEqual(state.removed["agent_0"].memory[0].round_id, 1)
        apply_population_intervention(state, InterventionSpec(2, "reintroduce_agent", target_agent="agent_0"))
        self.assertIn("agent_0", state.active)

    def test_initial_condition_and_scheduled_memory_intervention_are_logged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            probes = root / "probes.json"
            write_probe_set(probes, generate_probe_payload(HiddenWorldEnvironment(), per_world=1))
            initial = self._experience(0)
            config = RunConfig(
                experiment=ExperimentSettings(num_agents=2, num_rounds=2, checkpoints=(), technical_retries=0, console_summary=False),
                agent=AgentSettings(backend="mock"),
                condition=ConditionSettings(memory_mode="private"),
                initial_conditions=InitialConditionSettings(experiences=({"agent": "agent_0", **initial.prompt_dict()},)),
                interventions=({"trigger_round": 2, "operation": "memory_erase", "target_agent": "agent_0"},),
                logging=LoggingSettings(output_dir=str(root / "runs"), probe_set_path=str(probes)),
            )
            run_dir = asyncio.run(ExperimentRunner(config, backend=MockBackend()).run())
            events = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]
            self.assertTrue(any(event["event"] == "initial_condition" for event in events))
            self.assertTrue(any(event["event"] == "intervention" for event in events))
