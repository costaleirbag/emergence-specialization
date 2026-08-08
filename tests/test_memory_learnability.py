from __future__ import annotations

import unittest
from pathlib import Path

from emergent_specialization.agents import ExperimentalAgent
from emergent_specialization.environment import HiddenWorldEnvironment
from emergent_specialization.memory import MemoryPolicy
from emergent_specialization.memory_learnability import (
    build_contexts,
    expected_query_count,
    load_spec,
    preflight,
    _probe_map,
    _query_id,
)
from emergent_specialization.models import Task


class MemoryLearnabilityPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.spec, self.base, _ = load_spec(Path(__file__).resolve().parents[1] / "configs/research/memory_learnability_v1.yaml")
        self.probes, _ = _probe_map(Path(__file__).resolve().parents[1] / "data/probe_set.json")
        self.contexts = build_contexts(self.spec, self.base, self.probes)

    def test_expected_query_count_and_context_count(self) -> None:
        self.assertEqual(expected_query_count(self.spec), 9600)
        self.assertEqual(len(self.contexts), 320)
        self.assertEqual(preflight(Path(__file__).resolve().parents[1] / "configs/research/memory_learnability_v1.yaml")["probe_set_hash"], "cb234422389ff7d5a04566112a483f147e4a3d1212b1c69fbb0396ec9ca4c55e")

    def test_controls_have_declared_memory_semantics(self) -> None:
        for context in self.contexts:
            memory = context["memory"]
            target = context["target_world"]
            if context["mode"] == "unrelated_k8":
                self.assertFalse(any(item["world"] == target for item in memory))
            if context["mode"] == "mixed_k8":
                self.assertEqual({world: sum(item["world"] == world for item in memory) for world in self.spec["worlds"]}, {world: 2 for world in self.spec["worlds"]})
            if context["mode"] == "corrupted_k8":
                self.assertTrue(all(item["prediction"] != item["correct_answer"] for item in memory))

    def test_exemplars_are_disjoint_from_probes(self) -> None:
        for context in self.contexts:
            probe_tasks = {(item.world, item.x, item.y) for values in self.probes.values() for item in values}
            self.assertTrue(all((item["world"], item["x"], item["y"]) not in probe_tasks for item in context["memory"]))

    def test_replicate_query_ids_are_distinct(self) -> None:
        task = self.probes["ALPHA"][0]
        context = next(item for item in self.contexts if item["mode"] == "same_world" and item["target_world"] == "ALPHA" and item["k"] == 0)
        self.assertNotEqual(_query_id(context, task, 0), _query_id(context, task, 1))

    def test_prompt_reuses_memory_renderer_without_hidden_rule(self) -> None:
        context = next(item for item in self.contexts if item["mode"] == "same_world" and item["target_world"] == "BETA" and item["k"] == 1)
        agent = ExperimentalAgent("calibration_agent")
        task = Task(world="BETA", x=1, y=2, correct_answer=0, task_id="held-out")
        prompt, _ = agent.prompt_parts(task, MemoryPolicy("recent_k", 8), memory_snapshot=tuple(__import__("emergent_specialization.models", fromlist=["Experience"]).Experience(**item) for item in context["memory"]))
        self.assertNotIn("HIDDEN_RULES", prompt)
        self.assertNotIn("(1, 3, 2)", prompt)
