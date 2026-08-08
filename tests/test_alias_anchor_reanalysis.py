import unittest

from emergent_specialization.alias_anchor_reanalysis import displayed_memory_metrics, is_modular_alias


class AliasAnchorReanalysisTests(unittest.TestCase):
    def test_modular_alias_is_target_world_only(self):
        probe = {"x": 15, "y": 16}
        memory = [{"world": "ALPHA", "x": 1, "y": 2}, {"world": "BETA", "x": 8, "y": 10}]
        self.assertTrue(is_modular_alias(probe, memory, "ALPHA"))
        self.assertFalse(is_modular_alias(probe, memory, "BETA"))

    def test_displayed_recent_k_age_not_full_history_age(self):
        displayed = [{"round_id": 13, "correct_answer": 1, "prediction": 0}, {"round_id": 20, "correct_answer": 2, "prediction": 2}]
        metrics = displayed_memory_metrics(2, displayed, {0: .2, 1: .3, 2: .5}, 20)
        self.assertEqual(metrics["displayed_memory_size"], 2)
        self.assertEqual(metrics["mean_exposure_age"], 3.5)

    def test_conditional_null_arithmetic(self):
        memory = [{"round_id": 1, "correct_answer": 1, "prediction": 0}, {"round_id": 2, "correct_answer": 2, "prediction": 2}]
        metrics = displayed_memory_metrics(2, memory, {0: .1, 1: .3, 2: .4, 3: .2}, 2)
        self.assertEqual(metrics["any_label_match"], 1.0)
        self.assertAlmostEqual(metrics["any_label_null"], .7)
        self.assertEqual(metrics["last_label_null"], .4)
        self.assertEqual(metrics["last_prediction_null"], .4)


if __name__ == "__main__": unittest.main()
