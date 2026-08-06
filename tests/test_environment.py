from __future__ import annotations

import unittest

from emergent_specialization.environment import HIDDEN_RULES, HiddenWorldEnvironment, task_prompt


class HiddenWorldEnvironmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = HiddenWorldEnvironment()

    def test_documented_rules_are_deterministic(self) -> None:
        self.assertEqual(self.environment.answer_for("ALPHA", 3, 5), 5)
        self.assertEqual(self.environment.answer_for("BETA", 3, 5), 6)
        self.assertEqual(self.environment.answer_for("GAMMA", 3, 5), 1)
        self.assertEqual(self.environment.answer_for("DELTA", 3, 5), 3)

    def test_model_prompt_exposes_no_answer_or_rule_formula(self) -> None:
        task = self.environment.make_task("ALPHA", 3, 5)
        prompt = task_prompt(task)
        # Values can naturally coincide (here y and the correct answer are both
        # 5), so test for forbidden *fields/formulas*, not an isolated digit.
        self.assertNotIn("correct_answer", prompt)
        self.assertNotIn("the correct answer", prompt.lower())
        self.assertNotIn("2x+y+1", prompt.replace(" ", ""))
        self.assertNotIn("coefficient", prompt.lower())
        self.assertIn("World ALPHA", prompt)

    def test_all_enabled_worlds_have_a_hidden_rule(self) -> None:
        self.assertEqual(set(self.environment.worlds), set(HIDDEN_RULES))
