import collections
import inspect
import unittest

from emergent_specialization import cross_domain_transfer_bottleneck as bottleneck


class CrossDomainTransferBottleneckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks = bottleneck.build_tasks()

    def test_frozen_count_and_breakdown(self):
        self.assertEqual(len(self.tasks), 2944)
        self.assertEqual(bottleneck.expected_calls(), {"local": 384, "cross_per_arm": 512, "cross_arms": 5, "cross_total": 2560, "total": 2944})
        counts = collections.Counter(t["arm"] for t in self.tasks)
        self.assertEqual(counts["LOCAL_REP"], 384)
        for arm in bottleneck.CROSS_ARMS:
            self.assertEqual(counts[arm], 512)

    def test_true_same_population_and_source_identifiability(self):
        cross = [t for t in self.tasks if t["arm"] == "A0_RELATION_ONLY"]
        self.assertEqual(len(cross), 512)
        self.assertEqual(collections.Counter(t["geometry"] for t in cross), {"GLOBAL": 384, "BLOCK": 128})
        self.assertTrue(all(t["actual_relation"] == "SAME_POLICY" for t in cross))
        unique = {t["underlying_task_id"]: t for t in cross}
        self.assertGreaterEqual(sum(float(t["A_star_source"]) >= .99 for t in unique.values()) / len(unique), .90)

    def test_ladder_arms_and_order_are_deterministic(self):
        again = bottleneck.build_tasks()
        self.assertEqual([t["prompt_hash"] for t in self.tasks], [t["prompt_hash"] for t in again])
        self.assertEqual([t["execution_order"] for t in self.tasks], list(range(2944)))
        self.assertEqual([t["execution_order"] for t in again], list(range(2944)))

    def test_no_explicit_answer_leak_in_any_prompt(self):
        self.assertFalse(any(t["answer_leak"] for t in self.tasks))
        for arm in bottleneck.CROSS_ARMS:
            task = next(t for t in self.tasks if t["arm"] == arm)
            self.assertNotIn("GLOBAL", bottleneck.render_user(task))
            self.assertNotIn("BLOCK", bottleneck.render_user(task))
            self.assertNotIn("DIAGONAL", bottleneck.render_user(task))

    def test_representation_escalation_is_explicit(self):
        samples = {arm: next(t for t in self.tasks if t["arm"] == arm) for arm in bottleneck.ARMS}
        self.assertIn("Prior resolved cases", bottleneck.render_user(samples["A0_RELATION_ONLY"]))
        self.assertIn("correspondence", bottleneck.render_user(samples["A1_SEMANTIC_PI"]))
        self.assertIn("Canonical case", bottleneck.render_user(samples["A2_CANONICAL"]))
        self.assertIn("Policy dimension", bottleneck.render_user(samples["A3_RULE_SEMANTIC"]))
        self.assertIn("state 0", bottleneck.render_user(samples["A4_RULE_CANONICAL"]))

    def test_real_execution_requires_explicit_confirmation(self):
        source = inspect.getsource(bottleneck.run_real)
        self.assertIn("if not confirm_real", source)
        self.assertIn("DeepSeekDirectBackend", source)


if __name__ == "__main__":
    unittest.main()
