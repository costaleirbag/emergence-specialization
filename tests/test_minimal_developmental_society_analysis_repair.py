import itertools
import unittest
from unittest.mock import patch

import numpy as np

from emergent_specialization import minimal_developmental_society as society
from emergent_specialization.minimal_developmental_society_analysis_repair import (
    _make_cell,
    compare_aggregations,
    grouped_aggregation,
    pivot_aggregation,
    validate_matching,
)


class MinimalDevelopmentalSocietyAnalysisRepairTests(unittest.TestCase):
    def test_competence_cell_bounds_and_denominators(self):
        key = (1, "RP", 0, 0, "ACCESS")
        observations = [(f"p{i}", {"decisions": [1, 0, 1] if i < 4 else [0, 0, 0], "expected": [1, 0, 1]}) for i in range(16)]
        cell = _make_cell(key, observations)
        self.assertEqual(cell["n_probes"], 16)
        self.assertEqual(cell["n_bit_decisions"], 48)
        self.assertGreaterEqual(cell["accuracy"], 0)
        self.assertLessEqual(cell["accuracy"], 1)
        self.assertGreaterEqual(cell["bit_accuracy"], 0)
        self.assertLessEqual(cell["bit_accuracy"], 1)

    def test_niche_isolation(self):
        def make(value):
            return [(f"p{i}", {"decisions": [value, value, value], "expected": [1, 1, 1]}) for i in range(16)]
        a = _make_cell((1, "RP", 0, 0, "ACCESS"), make(1))
        b = _make_cell((1, "RP", 0, 0, "INCIDENT"), make(0))
        b_changed = _make_cell((1, "RP", 0, 0, "INCIDENT"), make(1))
        self.assertNotEqual(a["accuracy"], b["accuracy"])
        self.assertEqual(a["accuracy"], 1.0)
        self.assertEqual(b_changed["accuracy"], 1.0)

    def test_grouped_and_pivot_aggregation_are_identical(self):
        with patch.object(society, "SEEDS", (1,)), patch.object(society, "REGIMES", ("RP",)), patch.object(society, "CHECKPOINTS", (0,)), patch.object(society, "FAMILIES", ("ACCESS", "INCIDENT")), patch.object(society, "NUM_AGENTS", 2), patch.object(society, "EVAL_COUNT", 2):
            terminals = {}
            for agent, niche, probe in itertools.product(range(2), ("ACCESS", "INCIDENT"), range(2)):
                logical_id = society._call_id("t0", 1, "COMMON_T0", 0, agent, niche, probe)
                terminals[logical_id] = {"phase": "checkpoint", "seed": 1, "regime": "COMMON_T0", "checkpoint": 0, "agent": agent, "niche": niche, "task": {"probe_index": probe}, "decisions": [1, 0, 1] if probe == 0 else [0, 0, 0], "expected": [1, 0, 1]}
            grouped = grouped_aggregation(terminals)
            pivot = pivot_aggregation(terminals)
            self.assertEqual(compare_aggregations(grouped, pivot)["mismatch_count"], 0)
            self.assertEqual(len(grouped), 4)

    def test_matching_bruteforce_and_hungarian_match(self):
        rows = []
        matrix = np.array([[1.0, .2, .3, .4], [.1, .9, .2, .2], [.3, .1, .8, .2], [.2, .2, .1, .7]])
        for agent in range(4):
            for niche_index, niche in enumerate(society.FAMILIES):
                rows.append({"seed": 27101, "regime": "RP", "checkpoint": 0, "agent": agent, "niche": niche, "accuracy": matrix[agent, niche_index]})
        self.assertEqual(validate_matching(rows)["mismatch_count"], 0)

    def test_double_centering_permutation_invariance(self):
        matrix = np.array([[1.0, .2, .3, .4], [.1, .9, .2, .2], [.3, .1, .8, .2], [.2, .2, .1, .7]])
        row_perm = [2, 0, 3, 1]
        col_perm = [1, 3, 0, 2]
        permuted = matrix[np.ix_(row_perm, col_perm)]
        self.assertAlmostEqual(society.psi_spec(matrix), society.psi_spec(permuted))


if __name__ == "__main__":
    unittest.main()
