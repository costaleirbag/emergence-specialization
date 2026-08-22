import itertools
import math
import random
import unittest

from emergent_specialization.studies.ecology.ecological_information import FAMILIES, GEOMETRIES, generate_environment, sample_history
from emergent_specialization.studies.ecology.ecological_information_v31 import (
    EVAL_TEMPLATE_IDS,
    SEMANTIC_SCHEMAS,
    TRAIN_TEMPLATE_IDS,
    BlindObservableBayesLearner,
    ObservableEcologyBayesLearner,
    _aggregate_stats,
    _make_history,
    blind_decode_x,
    blind_o,
    decode_family,
    decode_x,
    observable_o,
    render_observable,
)


class ObservableInformationV31Tests(unittest.TestCase):
    def test_observable_schema_replays_family_and_x_without_ids(self):
        for family in FAMILIES:
            for x in itertools.product(range(4), repeat=3):
                o = observable_o(family, x)
                self.assertEqual(decode_family(o), family)
                self.assertEqual(decode_x(o), x)
                self.assertNotIn("family_id", o)
                self.assertNotIn("geometry", o)
                self.assertNotIn("theta", o)
                self.assertEqual(blind_decode_x(blind_o(o)), x)

    def test_renderer_is_deterministic_unique_and_split(self):
        texts = set()
        for family in FAMILIES:
            for x in itertools.product(range(4), repeat=3):
                o = observable_o(family, x)
                for template_id in range(4):
                    text = render_observable(o, family, template_id)
                    self.assertNotIn("theta", text.lower())
                    self.assertNotIn("geometry", text.lower())
                    self.assertNotIn("seed", text.lower())
                    self.assertNotIn("canonical dimension", text.lower())
                    self.assertNotIn(family, text)
                    self.assertNotIn(text, texts)
                    self.assertEqual(text, render_observable(o, family, template_id))
                    texts.add(text)
        self.assertEqual(set(TRAIN_TEMPLATE_IDS) | set(EVAL_TEMPLATE_IDS), {0, 1, 2, 3})
        self.assertTrue(set(TRAIN_TEMPLATE_IDS).isdisjoint(EVAL_TEMPLATE_IDS))

    def test_observable_learner_has_no_family_id_argument_and_matches_latent(self):
        env = generate_environment("BLOCK", 11)
        cases = sample_history(env, "ACCESS", 4, random.Random(11))
        history = [dict(observable_o("ACCESS", case.x), y=list(case.y)) for case in cases]
        target = observable_o("RELEASE", (0, 1, 2))
        learner = ObservableEcologyBayesLearner("BLOCK")
        probs = learner.predictive(history, target, (0, 1, 2))
        self.assertAlmostEqual(sum(probs), 1.0)
        # Exact replay must preserve the latent posterior for every query.
        from emergent_specialization.studies.ecology.ecological_information import posterior_predictive
        latent = posterior_predictive(env, "ACCESS", "RELEASE", cases, (0, 1, 2))
        self.assertEqual(probs, latent)

    def test_blind_control_does_not_accept_explicit_family(self):
        env = generate_environment("DIAGONAL", 12)
        cases = sample_history(env, "ACCESS", 8, random.Random(12))
        history = [dict(blind_o(observable_o("ACCESS", case.x)), y=list(case.y)) for case in cases]
        target = blind_o(observable_o("RELEASE", (0, 1, 2)))
        probs = BlindObservableBayesLearner("DIAGONAL").predictive(history, target, (0, 1, 2))
        self.assertAlmostEqual(sum(probs), 1.0)
        self.assertNotEqual(probs, (1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0))

    def test_histories_are_nested_prefixes(self):
        env = generate_environment("GLOBAL", 13)
        full, observable = _make_history(env, "ACCESS", 8, policy="natural", rng=random.Random(13))
        for left, right in ((1, 2), (2, 4), (4, 8)):
            self.assertEqual([case.x for case in full[:left]], [case.x for case in full[:right]][:left])
            self.assertEqual(observable[:left], observable[:right][:left])

    def test_component_stats_are_separate(self):
        stats = _aggregate_stats([(1 / 8,) * 8])
        for key in ("component_accuracy_1", "component_accuracy_2", "component_accuracy_3", "component_J_1", "component_J_2", "component_J_3"):
            self.assertIn(key, stats)
            self.assertTrue(math.isfinite(stats[key]))


if __name__ == "__main__":
    unittest.main()
