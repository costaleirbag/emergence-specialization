from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from emergent_specialization.config import (
    AgentSettings,
    ConditionSettings,
    ExperimentSettings,
    LoggingSettings,
    RunConfig,
)
from emergent_specialization.experiment import ExperimentRunner
from emergent_specialization.probes import generate_probe_payload, write_probe_set
from emergent_specialization.environment import HiddenWorldEnvironment
from emergent_specialization.providers.mock import MockBackend


class ExperimentRunnerTests(unittest.TestCase):
    def _run(self, mode: str) -> tuple[ExperimentRunner, Path]:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        probe_path = root / "probes.json"
        write_probe_set(probe_path, generate_probe_payload(HiddenWorldEnvironment(), per_world=1))
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
            condition=ConditionSettings(memory_mode=mode),
            logging=LoggingSettings(output_dir=str(root / "runs"), probe_set_path=str(probe_path)),
        )
        runner = ExperimentRunner(config, backend=MockBackend())
        run_dir = asyncio.run(runner.run())
        return runner, run_dir

    def test_private_feedback_updates_exactly_one_memory_per_round(self) -> None:
        runner, run_dir = self._run("private")
        self.assertEqual(sum(len(agent.memory) for agent in runner.agents), 2)
        events = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]
        rounds = [event for event in events if event["event"] == "round_complete"]
        self.assertEqual([len(event["feedback_recipients"]) for event in rounds], [1, 1])

    def test_shared_feedback_updates_every_memory_equally(self) -> None:
        runner, run_dir = self._run("shared")
        self.assertEqual([len(agent.memory) for agent in runner.agents], [2, 2, 2, 2])
        self.assertTrue(all(agent.memory == runner.agents[0].memory for agent in runner.agents[1:]))
        events = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]
        rounds = [event for event in events if event["event"] == "round_complete"]
        self.assertEqual([len(event["feedback_recipients"]) for event in rounds], [4, 4])

    def test_checkpoint_never_mutates_memory(self) -> None:
        runner, run_dir = self._run("private")
        checkpoints = [
            json.loads(line)
            for line in (run_dir / "events.jsonl").read_text().splitlines()
            if json.loads(line)["event"] == "checkpoint_complete"
        ]
        self.assertEqual([event["checkpoint"] for event in checkpoints], [0, 2])
        self.assertEqual(checkpoints[0]["memory_counts"], {"agent_0": 0, "agent_1": 0, "agent_2": 0, "agent_3": 0})
