from __future__ import annotations

import unittest

from emergent_specialization.agents import DEFAULT_SYSTEM_PROMPT, ExperimentalAgent, assert_initial_symmetry
from emergent_specialization.environment import HiddenWorldEnvironment
from emergent_specialization.memory import MemoryPolicy
from emergent_specialization.models import Experience


def experience(round_id: int) -> Experience:
    return Experience(round_id, "ALPHA", round_id, 2, 3, 0.7, 4, False)


class MemoryTests(unittest.TestCase):
    def test_recent_k_has_a_fixed_budget(self) -> None:
        policy = MemoryPolicy("recent_k", 2)
        records = policy.select([experience(1), experience(2), experience(3)])
        self.assertEqual([item.round_id for item in records], [2, 3])

    def test_prompt_does_not_include_agent_identity(self) -> None:
        environment = HiddenWorldEnvironment()
        task = environment.make_task("BETA", 2, 3)
        agents = [ExperimentalAgent("agent_0"), ExperimentalAgent("agent_1")]
        prompt_a, _ = agents[0].prompt_parts(task, MemoryPolicy())
        prompt_b, _ = agents[1].prompt_parts(task, MemoryPolicy())
        self.assertEqual(prompt_a, prompt_b)
        self.assertNotIn("agent_0", prompt_a)
        self.assertNotIn("agent_1", prompt_a)

    def test_initial_symmetry_requires_empty_memory(self) -> None:
        agents = [ExperimentalAgent("agent_0"), ExperimentalAgent("agent_1")]
        assert_initial_symmetry(agents, DEFAULT_SYSTEM_PROMPT)
        agents[0].observe(experience(1))
        with self.assertRaises(AssertionError):
            assert_initial_symmetry(agents, DEFAULT_SYSTEM_PROMPT)
