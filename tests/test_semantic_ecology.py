from __future__ import annotations

import unittest

from emergent_specialization.ar001b import generate_probes
from emergent_specialization.semantic_ecology import ECOLOGIES, OUTPUT_CLASSES, ROOT_CLASSES, predictive_identifiability
from emergent_specialization.ecology_transfer import build_tasks


class SemanticEcologyTests(unittest.TestCase):
    def test_ar001b_is_balanced_and_genuinely_two_dimensional(self):
        probes = generate_probes()
        self.assertEqual(len(probes), 56)
        self.assertEqual(sum(x["x"] != 0 and x["y"] != 0 for x in probes), 56)
        for world in {x["world"] for x in probes}:
            self.assertEqual({label: sum(x["world"] == world and x["correct_answer"] == label for x in probes) for label in range(7)}, {label: 2 for label in range(7)})

    def test_ecologies_replay_balance_and_identifiability(self):
        for ecology in ECOLOGIES.values():
            for seed in (0, 1, 99):
                env = ecology.generate_environment(seed)
                self.assertEqual(env, ecology.generate_environment(seed))
                for family in ecology.families:
                    probes = ecology.probe_cases(env, family)
                    self.assertEqual({label: sum(p.expected == label for p in probes) for label in ecology.output_classes}, {label: 2 for label in ecology.output_classes})
                    train = ecology.training_cases(env, family, 8)
                    self.assertTrue({x.case_id for x in probes}.isdisjoint({x.case_id for x in train}))
                    self.assertTrue(all(ecology.solve(env, family, p.fields) == p.expected for p in probes))
                    self.assertGreaterEqual(predictive_identifiability(ecology, env, family, 8)["predictively_identifiable"], 0.9)
                    rendered = "\n".join(ecology.render_case(family, p) for p in probes + train)
                    self.assertNotIn(family, rendered)
                    self.assertNotIn("theta", rendered.lower())

    def test_transfer_manifest_counts_and_nested_exposure(self):
        for ecology in ECOLOGIES.values():
            tasks = build_tasks(ecology, (1,))
            self.assertEqual(len(tasks), 384)
            for task in tasks:
                if task["h"] == 4:
                    matching = [x for x in tasks if x["seed"] == task["seed"] and x["target"] == task["target"] and x["source"] == task["source"] and x["h"] == 8 and x["case"]["case_id"] == task["case"]["case_id"] and x["replicate"] == task["replicate"]]
                    self.assertEqual(len(matching), 1)
                    self.assertEqual(task["memory"], matching[0]["memory"][:4])


if __name__ == "__main__":
    unittest.main()
