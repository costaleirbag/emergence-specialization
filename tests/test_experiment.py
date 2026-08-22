from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from emergent_specialization.core.config import (
    AgentSettings,
    ConditionSettings,
    CostSettings,
    ExperimentSettings,
    LoggingSettings,
    RunConfig,
)
from emergent_specialization.runtime.experiment import ExperimentRunner
from emergent_specialization.core.models import BackendResponse
from emergent_specialization.core.probes import generate_probe_payload, write_probe_set
from emergent_specialization.core.environment import HiddenWorldEnvironment
from emergent_specialization.providers.mock import MockBackend


class UsageMockBackend(MockBackend):
    async def complete(self, **kwargs: object) -> BackendResponse:
        response = await super().complete(**kwargs)  # type: ignore[arg-type]
        return replace(
            response,
            token_usage={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
        )


class OutOfDomainBackend:
    """Return a syntactically valid but scientifically wrong answer."""

    def metadata(self) -> dict[str, str]:
        return {"backend": "test-out-of-domain"}

    async def complete(self, **kwargs: object) -> BackendResponse:
        return BackendResponse(
            raw_response='{"answer": 7, "confidence": 0.2}',
            latency_s=0.0,
        )


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

    def test_summary_reports_usage_and_configured_cost_without_provider_calls(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        probe_path = root / "probes.json"
        write_probe_set(probe_path, generate_probe_payload(HiddenWorldEnvironment(), per_world=1))
        config = RunConfig(
            experiment=ExperimentSettings(
                num_agents=2,
                num_rounds=1,
                checkpoints=(),
                max_concurrency=2,
                technical_retries=0,
                console_summary=False,
            ),
            agent=AgentSettings(backend="mock"),
            condition=ConditionSettings(memory_mode="private"),
            logging=LoggingSettings(output_dir=str(root / "runs"), probe_set_path=str(probe_path)),
            cost=CostSettings(input_per_million_tokens=1.0, output_per_million_tokens=2.0),
        )
        run_dir = asyncio.run(ExperimentRunner(config, backend=UsageMockBackend()).run())
        summary = json.loads((run_dir / "summary.json").read_text())
        self.assertEqual(summary["usage"]["status"], "estimated")
        self.assertEqual(summary["usage"]["calls_total"], 2)
        self.assertEqual(summary["usage"]["total_tokens"], 240)
        self.assertAlmostEqual(summary["usage"]["estimated_cost"], 0.00028)

    def test_out_of_domain_answer_is_completed_without_retry_and_keeps_prediction(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        probe_path = root / "probes.json"
        write_probe_set(probe_path, generate_probe_payload(HiddenWorldEnvironment(), per_world=1))
        config = RunConfig(
            experiment=ExperimentSettings(
                num_agents=2,
                num_rounds=1,
                checkpoints=(0, 1),
                max_concurrency=2,
                technical_retries=1,
                console_summary=False,
            ),
            agent=AgentSettings(backend="mock"),
            condition=ConditionSettings(memory_mode="private"),
            logging=LoggingSettings(output_dir=str(root / "runs"), probe_set_path=str(probe_path)),
        )
        run_dir = asyncio.run(ExperimentRunner(config, backend=OutOfDomainBackend()).run())
        events = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]
        inference = [event for event in events if event["event"] == "inference"]
        # Two interaction completions plus two checkpoints with four probes
        # for each of the two agents: 2 + (2 * 4 * 2) = 18.
        self.assertEqual(len(inference), 18)  # no retry
        self.assertTrue(all(event["error"] is None for event in inference))
        self.assertTrue(all(event["answer_in_domain"] is False for event in inference))
        self.assertTrue(all(event["semantic_violation"] == "answer_out_of_domain" for event in inference))
        rounds = [event for event in events if event["event"] == "round_complete"]
        self.assertEqual(rounds[0]["selected_answer"], 7)
        self.assertFalse(rounds[0]["selected_correct"])
        self.assertEqual(rounds[0]["feedback_recipients"], [rounds[0]["selected_agent_id"]])
        self.assertEqual(rounds[0]["candidates"][rounds[0]["selected_agent_id"]]["answer"], 7)
        summary = json.loads((run_dir / "summary.json").read_text())
        self.assertEqual(summary["status"], "completed")
