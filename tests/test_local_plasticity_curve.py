import collections
import unittest

from emergent_specialization.studies.calibration import local_plasticity_curve as curve


class LocalPlasticityCurveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = curve.substrate_audit()
        cls.tasks = curve.build_tasks()

    def test_v2_substrate_audit_passes(self):
        self.assertTrue(self.audit["checks"]["all_pass"], self.audit)

    def test_exact_count_breakdown(self):
        self.assertEqual(len(self.tasks), 2176)
        self.assertEqual(curve.expected_calls(), {"empty": 128, "same": 512, "foreign": 1536, "total": 2176})
        self.assertEqual(collections.Counter(task["condition"] for task in self.tasks), {"EMPTY": 128, "SAME": 512, "FOREIGN": 1536})

    def test_only_diagonal_and_frozen_horizons(self):
        self.assertEqual({task["geometry"] for task in self.tasks}, {"DIAGONAL"})
        self.assertEqual({task["h"] for task in self.tasks}, {0, 1, 2, 4, 8})
        self.assertEqual({task["condition"] for task in self.tasks}, {"EMPTY", "SAME", "FOREIGN"})

    def test_histories_are_nested_and_foreign_uses_all_sources(self):
        for seed in curve.SEEDS:
            for target in curve.FAMILIES:
                for probe in [task for task in self.tasks if task["seed"] == seed and task["target"] == target and task["condition"] == "EMPTY"]:
                    for condition in ("SAME", "FOREIGN"):
                        rows = [task for task in self.tasks if task["seed"] == seed and task["target"] == target and task["probe"]["case_id"] == probe["probe"]["case_id"] and task["condition"] == condition]
                        for row in rows:
                            self.assertEqual(len(row["memory"]), row["h"])
                            self.assertEqual(row["history_ids"], [item["case_id"] for item in row["memory"]])

    def test_no_static_answer_vector_or_forbidden_scaffolding(self):
        self.assertEqual(curve.v2.static_triplet_leaks(), [])
        sample = next(task for task in self.tasks if task["condition"] == "SAME" and task["h"] == 8)
        rendered = curve.v2.render_user(sample)
        for forbidden in ("DIAGONAL", "GLOBAL", "BLOCK", "canonical", "correspondence", "relation"):
            self.assertNotIn(forbidden, rendered)

    def test_foreign_bayes_opportunity_is_empty_baseline(self):
        for task in self.tasks:
            if task["condition"] == "FOREIGN":
                self.assertAlmostEqual(float(task["A_star_prompt"]), 0.125, places=12)


if __name__ == "__main__":
    unittest.main()
