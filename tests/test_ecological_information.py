import math
import random
import unittest

from emergent_specialization.studies.ecology.ecological_information import (
    BALANCED_MAPS,
    FAMILIES,
    GEOMETRIES,
    V3Case,
    all_symbolic_cases,
    entropy_bits,
    generate_environment,
    posterior_predictive,
    render_case,
    sample_history,
    solve,
    teaching_history,
    estimate_v3,
)


class EcologicalInformationTests(unittest.TestCase):
    def test_balanced_maps_and_cases(self):
        self.assertEqual(len(BALANCED_MAPS), 6)
        self.assertTrue(all(sum(m) == 2 for m in BALANCED_MAPS))
        self.assertEqual(len(all_symbolic_cases("ACCESS")), 64)
        self.assertEqual(len({c.case_id for c in all_symbolic_cases("ACCESS")}), 64)

    def test_geometry_incidence(self):
        self.assertEqual(len({generate_environment("GLOBAL", 1).theta_by_family[f] for f in FAMILIES}), 1)
        block = generate_environment("BLOCK", 1)
        self.assertEqual(block.theta_by_family["ACCESS"], block.theta_by_family["RELEASE"])
        self.assertEqual(block.theta_by_family["INCIDENT"], block.theta_by_family["PROVENANCE"])
        diagonal = generate_environment("DIAGONAL", 1)
        self.assertEqual(diagonal.group_by_family, {f: i for i, f in enumerate(FAMILIES)})

    def test_factor_locality_and_no_semantic_leakage(self):
        env = generate_environment("DIAGONAL", 4)
        for family in FAMILIES:
            for case in all_symbolic_cases(family):
                solved = V3Case(family, case.x, solve(env.theta_by_family[family], case.x))
                rendered = render_case(solved)
                self.assertNotIn("DIAGONAL", rendered)
                self.assertNotIn("theta", rendered.lower())
                self.assertNotIn("geometry", rendered.lower())
                self.assertNotIn(family.lower(), rendered.lower())
                self.assertEqual(solved.y, solve(env.theta_by_family[family], solved.x))

    def test_h0_prior_is_uniform(self):
        env = generate_environment("GLOBAL", 2)
        probs = posterior_predictive(env, "ACCESS", "PROVENANCE", [], (0, 1, 2))
        self.assertEqual(len(probs), 8)
        self.assertTrue(all(math.isclose(p, 1 / 8) for p in probs))
        self.assertAlmostEqual(entropy_bits(probs), 3.0)

    def test_same_group_evidence_and_independent_group(self):
        env = generate_environment("BLOCK", 3)
        history = sample_history(env, "ACCESS", 8, random.Random(3))
        same = posterior_predictive(env, "ACCESS", "RELEASE", history, (0, 1, 2))
        cross = posterior_predictive(env, "ACCESS", "INCIDENT", history, (0, 1, 2))
        self.assertGreater(entropy_bits(cross), entropy_bits(same))
        self.assertTrue(all(math.isclose(p, 1 / 8) for p in cross))

    def test_teaching_is_distinct_from_natural(self):
        env = generate_environment("GLOBAL", 5)
        natural = sample_history(env, "ACCESS", 4, random.Random(5))
        teaching = teaching_history(env, "ACCESS", 4)
        self.assertEqual(len(natural), len(teaching),)
        self.assertNotEqual([x.x for x in natural], [x.x for x in teaching])

    def test_nested_information_non_decreasing(self):
        rows = estimate_v3(2, horizons=(0, 1, 2), include_teaching=False)
        values = [next(float(r["J_bits"]) for r in rows if r["geometry"] == "DIAGONAL" and
                       r["source"] == r["target"] == "ACCESS" and r["h"] == h) for h in (0, 1, 2)]
        self.assertLessEqual(values[0], values[1] + 1e-12)
        self.assertLessEqual(values[1], values[2] + 1e-12)

    def test_exact_independent_cross_cell_zero(self):
        env = generate_environment("DIAGONAL", 7)
        history = sample_history(env, "ACCESS", 8, random.Random(7))
        probs = posterior_predictive(env, "ACCESS", "INCIDENT", history, (1, 2, 3))
        self.assertTrue(all(math.isclose(p, 1 / 8) for p in probs))


if __name__ == "__main__":
    unittest.main()
