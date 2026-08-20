from __future__ import annotations

import unittest

from emergent_specialization.minimal_model import MinimalModelConfig, simulate


class MinimalModelTests(unittest.TestCase):
    def test_simulation_is_deterministic_for_a_fixed_seed(self) -> None:
        config = MinimalModelConfig(rounds=8, seed=7)
        self.assertEqual(simulate(config), simulate(config))

    def test_trajectory_contains_initial_and_final_skill_snapshots(self) -> None:
        result = simulate(MinimalModelConfig(num_agents=3, num_tasks=2, rounds=5))
        self.assertEqual(len(result.skills), 6)
        self.assertEqual(len(result.final_skills), 3)
        self.assertEqual(len(result.final_skills[0]), 2)

    def test_shared_feedback_updates_all_recipients_when_learning_occurs(self) -> None:
        result = simulate(MinimalModelConfig(num_agents=2, num_tasks=1, rounds=1, private_probability=0.0, seed=2))
        event = result.selections[0]
        self.assertEqual(event["recipients"], [0, 1])
