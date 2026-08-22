import collections
import inspect
import unittest

from emergent_specialization.studies.calibration import relation_signal_transfer as relation


class RelationSignalCausalTransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks = relation.build_tasks()

    def test_frozen_count_and_arm_balance(self):
        self.assertEqual(len(cls_tasks := self.tasks), 3456)
        self.assertEqual(relation.expected_calls(), {"underlying": 1152, "arms": 3, "total": 3456})
        self.assertEqual(collections.Counter(task["arm"] for task in cls_tasks), {"R0": 1152, "RS": 1152, "RI": 1152})

    def test_underlying_tasks_have_exactly_three_paired_arms(self):
        groups = collections.defaultdict(list)
        for task in self.tasks:
            groups[task["underlying_task_id"]].append(task)
        self.assertEqual(len(groups), 1152)
        self.assertTrue(all({task["arm"] for task in values} == set(relation.ARMS) for values in groups.values()))
        self.assertTrue(all(len(values) == 3 for values in groups.values()))

    def test_source_identifiability_gate_is_frozen_and_passes(self):
        groups = {}
        for task in self.tasks:
            groups.setdefault(task["underlying_task_id"], task)
        identifiable = sum(float(task["A_star_source"]) >= 0.99 for task in groups.values())
        self.assertEqual(len(groups), 1152)
        self.assertGreaterEqual(identifiable / len(groups), 0.90)

    def test_cues_have_no_regime_or_theta_leak(self):
        for cue in relation.CUE_STRINGS.values():
            self.assertNotIn("GLOBAL", cue)
            self.assertNotIn("BLOCK", cue)
            self.assertNotIn("DIAGONAL", cue)
            self.assertNotIn("theta", cue.lower())
            self.assertNotIn("factor", cue.lower())
        for task in self.tasks[::257]:
            rendered = relation.render_user(task, task["arm"])
            self.assertTrue(rendered.startswith(relation.CUE_STRINGS[task["arm"]]))
            self.assertNotIn(task["geometry"], relation.CUE_STRINGS[task["arm"]])

    def test_execution_order_is_deterministic_and_complete(self):
        again = relation.build_tasks()
        self.assertEqual([task["execution_order"] for task in self.tasks], list(range(3456)))
        self.assertEqual([task["prompt_hash"] for task in self.tasks], [task["prompt_hash"] for task in again])
        self.assertEqual([task["underlying_task_id"] for task in self.tasks], [task["underlying_task_id"] for task in again])

    def test_real_execution_requires_explicit_confirmation(self):
        source = inspect.getsource(relation.run_real)
        self.assertIn("if not confirm_real", source)
        self.assertIn("DeepSeekDirectBackend", source)


if __name__ == "__main__":
    unittest.main()
